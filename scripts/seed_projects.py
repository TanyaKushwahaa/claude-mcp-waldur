"""
Seed a Waldur instance with fake projects for load-testing the MCP tools.

Usage:
    python scripts/seed_projects.py --count 500
    python scripts/seed_projects.py --cleanup     # delete everything seed-* created

Reads WALDUR_BASE_URL and a staff token from .env. Run against a DEV instance
only — this will create hundreds of rows.
"""
import argparse
import asyncio
import os
import random
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ["WALDUR_BASE_URL"]
TOKEN = os.environ["WALDUR_API_TOKEN"]   # add this to your .env for the script
VERIFY_SSL = os.environ.get("VERIFY_SSL", "True").lower() == "true"

HEADERS = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

# Pretend institutions — these should already exist as customers in your dev Waldur,
# or the script will create them. Adjust the list to match what's there.
FAKE_CUSTOMERS = [
    "Seed University of Bristol",
    "Seed Cardiff University",
    "Seed Imperial College",
    "Seed University of Edinburgh",
    "Seed University of Manchester",
    "Seed UCL",
    "Seed University of Oxford",
    "Seed University of Cambridge",
]

NAME_THEMES = [
    "climate", "genomics", "fluid-dynamics", "ml-training", "quantum",
    "astrophysics", "materials", "chemistry", "epidemiology", "robotics",
]


async def ensure_customer(client: httpx.AsyncClient, name: str) -> str:
    """Return UUID of customer with this name, creating it if needed."""
    r = await client.get(f"{BASE_URL}customers/", headers=HEADERS,
                         params={"name_exact": name, "field": ["uuid", "name"]})
    r.raise_for_status()
    data = r.json()
    if data:
        return data[0]["uuid"]

    r = await client.post(f"{BASE_URL}customers/", headers=HEADERS,
                          json={"name": name, "abbreviation": name[:8].lower().replace(" ", "")})
    r.raise_for_status()
    return r.json()["uuid"]


async def create_project(client: httpx.AsyncClient, customer_uuid: str, idx: int):
    theme = random.choice(NAME_THEMES)
    name = f"seed-{theme}-{idx:04d}"
    short = f"sd{idx:04d}"

    payload = {
        "name": name,
        "short_name": short,
        "customer": f"{BASE_URL}customers/{customer_uuid}/",
        "description": f"Auto-generated load-test project #{idx}",
    }
    r = await client.post(f"{BASE_URL}projects/", headers=HEADERS, json=payload)
    if r.status_code not in (200, 201):
        return False, r.text[:200]
    return True, None


async def seed(count: int, concurrency: int = 10):
    async with httpx.AsyncClient(verify=VERIFY_SSL, follow_redirects=True, timeout=30.0) as client:
        # Make sure all fake customers exist
        print(f"Ensuring {len(FAKE_CUSTOMERS)} customers exist...")
        customer_uuids = []
        for name in FAKE_CUSTOMERS:
            uuid = await ensure_customer(client, name)
            customer_uuids.append(uuid)
            print(f"  {name}: {uuid}")

        # Create projects with bounded concurrency
        sem = asyncio.Semaphore(concurrency)
        successes = 0
        failures = []

        async def one(i):
            nonlocal successes
            async with sem:
                ok, err = await create_project(client, random.choice(customer_uuids), i)
                if ok:
                    successes += 1
                    if successes % 25 == 0:
                        print(f"  created {successes}/{count}")
                else:
                    failures.append((i, err))

        await asyncio.gather(*[one(i) for i in range(count)])
        print(f"\nDone: {successes} created, {len(failures)} failed")
        if failures:
            print("First 3 failures:")
            for i, err in failures[:3]:
                print(f"  #{i}: {err}")


async def cleanup():
    async with httpx.AsyncClient(verify=VERIFY_SSL, follow_redirects=True, timeout=30.0) as client:
        deleted = 0
        while True:
            r = await client.get(f"{BASE_URL}projects/", headers=HEADERS,
                                 params={"name": "seed-", "page_size": 100,
                                         "field": ["uuid", "name"]})
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            for row in rows:
                # Defensive: only delete things prefixed seed-
                if not row["name"].startswith("seed-"):
                    continue
                d = await client.delete(f"{BASE_URL}projects/{row['uuid']}/", headers=HEADERS)
                if d.status_code in (204, 202):
                    deleted += 1
            print(f"  deleted {deleted} so far...")
        print(f"\nCleanup done: {deleted} projects removed")
        print("Note: seed customers were NOT deleted — remove manually if you want.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--cleanup", action="store_true")
    args = p.parse_args()

    if args.cleanup:
        asyncio.run(cleanup())
    else:
        asyncio.run(seed(args.count))


if __name__ == "__main__":
    main()