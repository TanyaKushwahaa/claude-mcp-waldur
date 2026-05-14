# src/waldur_summary_tools.py
"""
Server-side aggregation tools for Waldur.

These stream through paginated Waldur endpoints inside the MCP process and
return ONLY aggregates — never raw rows — so the LLM context stays small
even when the underlying table has thousands of records.

Use these for any statistical / dashboard / over-time question.
Use get_from_waldur only for listing specific named records.
"""

import json
import logging
from collections import Counter
from datetime import datetime
from typing import Literal

import httpx

from src.mcp_instance import mcp
from src.utils import normalise_waldur_token
from config import WALDUR_BASE_URL, VERIFY_SSL

logger = logging.getLogger(__name__)


async def _stream_endpoint(token: str, method: str, params: dict, page_size: int = 200):
    """
    Async generator yielding rows from a Waldur list endpoint one at a time.
    Never accumulates more than one page in memory.
    """
    url = WALDUR_BASE_URL + f"{method}/"
    headers = {"Authorization": token}
    page = 1

    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL, timeout=30.0) as client:
        while True:
            page_params = {**params, "page": page, "page_size": page_size}
            try:
                resp = await client.get(url, headers=headers, params=page_params)
            except Exception as e:
                raise RuntimeError(f"Connection error on {method} page {page}: {e}")

            if resp.status_code == 401:
                raise RuntimeError("Authentication failed. Check your Waldur API token.")
            if resp.status_code == 403:
                raise RuntimeError("Access denied for this operation.")
            if resp.status_code == 404:
                return
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Waldur {method} page {page}: HTTP {resp.status_code}")

            rows = resp.json()
            if not isinstance(rows, list) or not rows:
                return

            for row in rows:
                yield row

            if len(rows) < page_size:
                return
            page += 1


def _month_bucket(iso_string):
    """Convert an ISO datetime to a YYYY-MM bucket label, or None if unparseable."""
    if not iso_string:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_string).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


@mcp.tool()
async def summarise_from_waldur(
    WALDUR_API_TOKEN: str,
    method: str,
    group_by: Literal["customer_name", "month_created", "state", "none"] = "customer_name",
    filters: dict | None = None,
    top_n: int = 20,
) -> str:
    """
    Aggregate a Waldur list endpoint server-side and return ONLY bucket counts.

    Use this tool for: "how many X per Y", "summarise X across all customers",
    "X over time", "distribution of X", or any question about totals/counts
    that would otherwise require listing thousands of rows.

    DO NOT use get_from_waldur with fetch_all_pages=True to answer aggregate
    questions — that will exhaust the context budget on large Waldur instances.
    Use this tool instead.

    Args:
        WALDUR_API_TOKEN (str): Waldur API token.
        method (str): Endpoint name (no leading slash, no trailing slash):
                      "projects", "users", "customers", "marketplace-resources",
                      "marketplace-orders", "user-invitations", etc.
        group_by (str): How to bucket the rows. One of:
            - "customer_name": group by parent organisation/institution
                (best for: distribution by university)
            - "month_created": group by YYYY-MM of the `created` field
                (best for: onboarding-over-time, growth charts)
            - "state": group by `state` field
                (best for: resources by lifecycle stage; works on marketplace endpoints)
            - "none": just return total count, no buckets
                (best for: "how many X are there total?")
        filters (dict | None): Optional Waldur query parameters to narrow the set
            BEFORE aggregating. Examples:
                {"customer": "<customer_uuid>"}  → only projects under that customer
                {"state": "OK"}                   → only resources in OK state
            DO NOT put group_by or top_n in here — those are tool params, not filters.
        top_n (int): Return only the top-N buckets by count. Buckets outside the
            top-N are summed into a single "_other" entry. Default 20.

    Returns:
        JSON string with:
            method: the endpoint queried
            group_by: how rows were bucketed
            filters: filters that were applied
            total: total rows across all buckets
            unique_buckets: how many distinct buckets existed before top-N truncation
            buckets: {bucket_name: count}  (sorted by count descending)

    Example:
        summarise_from_waldur(token, "projects", group_by="customer_name")
            → {"total": 537, "buckets": {"Bristol": 117, "Cardiff": 89, ...}}
        summarise_from_waldur(token, "projects", group_by="month_created")
            → {"total": 537, "buckets": {"2025-09": 42, "2025-10": 88, ...}}
    """
    token = normalise_waldur_token(WALDUR_API_TOKEN)

    # Only fetch the field we need to bucket on — keeps each page small.
    field_for_group = {
        "customer_name": ["customer_name"],
        "month_created": ["created"],
        "state": ["state"],
        "none": ["uuid"],  # need something, uuid is always small
    }
    params = dict(filters or {})
    params["field"] = field_for_group[group_by]

    counts: Counter = Counter()
    total = 0

    try:
        async for row in _stream_endpoint(token, method, params):
            total += 1
            if group_by == "none":
                continue
            if group_by == "month_created":
                key = _month_bucket(row.get("created")) or "unknown"
            else:
                key = row.get(group_by) or "unknown"
            counts[key] += 1
    except RuntimeError as e:
        return json.dumps({"error": str(e), "method": method, "filters": filters or {}})

    if group_by == "none":
        return json.dumps({
            "method": method,
            "filters": filters or {},
            "total": total,
        })

    top = dict(counts.most_common(top_n))
    other = sum(v for k, v in counts.items() if k not in top)
    if other > 0:
        top["_other"] = other

    return json.dumps({
        "method": method,
        "group_by": group_by,
        "filters": filters or {},
        "total": total,
        "unique_buckets": len(counts),
        "buckets": top,
    }, default=str)