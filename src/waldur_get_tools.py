# src/tools/waldur_get_tools.py
from config import WALDUR_BASE_URL, VERIFY_SSL
from src.mcp_instance import mcp
import httpx
import logging
from src.utils import normalise_waldur_token

logger = logging.getLogger(__name__)

# MCP Tool to retrieve UUIDs for various entities in Waldur
@mcp.tool()
async def get_uuid(
    WALDUR_API_TOKEN: str,
    short_name: str | None=None, 
    entity: str | None=None
    ) -> str | dict:
    '''
    This tool takes the Waldur API token and retrieves the UUID of an entity (e.g., project, customer, or user) given its short_name.

    Args: 
    - WALDUR_API_TOKEN (str): Waldur API Token
    - short_name (str): Short name of the entity (different from name)
    - entity (str): Type of entity, e.g., projects, customers, users, customer-credits, 
    project-credits, roles, slurm allocations, slurm-jobs, user-invitations, invoice, 
    marketplace-service-providers etc.

    Returns: 
    - str or dict: UUID string or an elicitation dict if parameters are missing/errors.
    '''

    if not WALDUR_API_TOKEN:
        return "Missing Waldur API token."

    if not entity:
        return {
            "type": "elicitation/create",
            "params": {
                "message": "For which entity do you want the UUID?",
                "requestedSchema": {
                    "type": "object",
                    "properties": {
                        "entity": {
                            "type": "string",
                            "description": "The name of the entity (e.g., projects)"
                        }
                    },
                    "required": ["entity"],
                },
            },
        }

    if entity == "projects" or entity == "customers":
        if not short_name:
            return {
                "type": "elicitation/create",
                "params": {
                    "message": f"Please provide the short name of the {entity}.",
                "requestedSchema": {
                    "type": "object",
                    "properties": {
                        "short_name": {
                            "type": "string",
                            "description": f"The short name of the {entity} (e.g., bri-sci-pro)"
                        }
                    },
                    "required": ["short_name"],
                },
            },
        }

    endpoint_map = {"projects": "projects/",
                    "users": "users/",
                    "customers": "customers/",
                    "customer-credits": "customer-credits/",
                    "project-credits": "project-credits/",
                    "roles": "roles/",
                    "slurm-allocations": "slurm-allocations/",
                    "slurm-jobs": "slurm-jobs/",
                    "user-invitations": "user-invitations/",
                    "invoice": "invoices/",
                    "marketplace-service-providers": "marketplace-service-providers/",
                    "marketplace-offerings": "marketplace-offerings/",
                    "marketplace-orders": "marketplace-orders/",
                    "marketplace-resource": "marketplace-resources/",
                    "marketplace-plans": "marketplace-plans/",
                    "marketplace-provider-offerings": "marketplace-provider-offerings/",
                    "marketplace-offering-permissions": "marketplace-offering-permissions/"
                    }

    
    if entity not in endpoint_map:
        return f"Sorry, I do not recognise the entity type '{entity}'."
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)
    url = WALDUR_BASE_URL + endpoint_map[entity]
    headers = {
        "Authorization": WALDUR_API_TOKEN
    }
    params = {
        "short_name": short_name
    }

    async with httpx.AsyncClient(follow_redirects=False, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    uuid = data[0].get("uuid")
                    if uuid:
                        return uuid
                    return f"I found {entity} but it has no UUID field."
                if short_name:
                    return f"No {entity} found with short_name '{short_name}'."
                else:
                    return f"No {entity} found matching the criteria."
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 404:
                if short_name:
                    return f"No {entity} found with short_name '{short_name}'."
                else: 
                    return f"No {entity} found matching the criteria."
            else:
                return f"API returned status error: {response.status_code}."
        except Exception as e: 
            return f"Error connecting to the server: {e}"
    

@mcp.tool()
async def get_from_waldur(parsed_intent: dict) -> str:
    """
    This MCP tool makes a Waldur API call using the parsed intent.

    parsed_intent should include:
    - WALDUR_API_TOKEN (str)
    - method (str): API endpoint (e.g., 'projects', 'customers', 'users',
                    'marketplace-resources', etc.)
    - http_method (str): 'GET'
    - payload (dict): Query parameters for filtering results
    - max_results (int, optional): cap on rows returned. None = use default.
    - fetch_all_pages (bool, optional): if True, paginate through every page.
                                        Default False = first page only.

    Example input:
    parsed_intent = {
        "WALDUR_API_TOKEN": "Token 2b2b323ki3hinrknfwdwd2322",
        "method": "projects",
        "http_method": "GET",
        "payload": {"name": "Quantum Research"}
    }

    ============================================
    PAGINATION (CRITICAL — READ FIRST)
    ============================================
    By DEFAULT this tool returns ONLY the first page (≤100 rows). The response
    includes "total_available" so you can see how many rows exist on the server,
    and "truncated": true if there are more.

    DO THIS for almost every query:
    - Pass narrow filters in payload (e.g. {"name": "Bristol", "customer": "<uuid>"}).
    - Read the first page; if total_available > returned_count, decide what to do.
    - For specific records: tell the user there are N matches, ask which one,
      or filter more tightly. DO NOT paginate to find one row.

    DO NOT use fetch_all_pages=True unless:
    - The user explicitly asks for "all" of something AND the total is small
      (under a few hundred), AND
    - You actually need every row in context to answer the question.

    For statistical questions ("how many projects per institution?", "onboarding
    over time", "summarise usage across customers") DO NOT list everything and
    count it in your head. Use summarise_from_waldur if available, or tell the
    user you cannot summarise the full dataset through listing.

    For "top N" or "biggest consumers" questions, use top_n_from_waldur if
    available. Listing all rows and sorting in context will exhaust the token
    budget on large Waldur instances (thousands of projects/users).

    Use max_results=N when the user asks for a bounded list ("show me 20
    projects", "first 50 users"). This is more efficient than fetching a full
    page and slicing.

    ============================================
    FIELD FILTERING (TOKEN EFFICIENCY)
    ============================================
    By default this tool returns only essential fields per entity to minimise
    token usage. To request specific fields, include them in payload:
        {"field": ["uuid", "name", "email"]}

    ALWAYS use field filtering when you only need specific information.
    Example: If you just need project names and UUIDs:
        {"name": "Research", "field": ["uuid", "name"]}

    ============================================
    FILTERING & SEARCH PARAMETERS
    ============================================
    The Waldur API supports various filter parameters. Common patterns:
    - Most resources support filtering by "name" (partial match, case-insensitive)
    - To filter by related resources, use the resource name (singular) with UUID:
      * Projects by organization: {"customer": "uuid"}
      * Resources by project: {"project": "uuid"}
    - Field names typically match the resource attribute names

    When unsure about available filters:
    1. Try common patterns first (name, uuid, related resource names)
    2. Make a test call with minimal filters and examine the response structure
    3. Response fields often indicate what can be filtered

    ============================================
    PARSING HIERARCHICAL NAMES
    ============================================
    When users mention "Project X in Organisation Y":
    1. Search for the organisation (customer) by name first
    2. Then search for the project by name within that organisation
    3. DO NOT concatenate names (e.g., searching for "Project X in
       Organisation Y" as a single project name)

    Example: "Add user to Scientific Research in Bristol University"
    Step 1: Find customer "Bristol University"
    Step 2: Find project "Scientific Research"
    DO NOT search for project named "Scientific Research in Bristol University"

    ============================================
    ERROR HANDLING
    ============================================
    - If a resource is not found, inform the user and ask for clarification
    - NEVER assume or hallucinate data
    - If the API is unreachable, state this clearly
    - For ambiguous queries, ask the user to clarify before making assumptions

    Returns:
        str: JSON string containing:
            - returned_count (int): Number of rows in this response
            - total_available (int): Total rows available on server
            - truncated (bool): True if more rows exist that weren't returned
            - method (str): The endpoint queried
            - data (list): Array of objects with requested/essential fields
            - hint (str | null): Guidance for next step if truncated
    """
    WALDUR_API_TOKEN = parsed_intent['WALDUR_API_TOKEN']
    method = parsed_intent['method']
    http_method = parsed_intent['http_method']
    payload = dict(parsed_intent.get('payload', {}))
    max_results = parsed_intent.get('max_results')
    fetch_all_pages = parsed_intent.get('fetch_all_pages', False)
    
    # Define essential fields for each entity type
    essential_fields = {
        'customers': ['uuid', 'name', 'abbreviation', 'projects_count', 'users_count', 'email'],
        'projects': ['uuid', 'name', 'short_name', 'customer_name', 'created', 'start_date', 'end_date'],
        'users': ['uuid', 'username', 'email', 'full_name', 'is_staff'],
        'user-invitations': ['email', 'created', 'state'],
        'marketplace-resources': ['uuid', 'name', 'state', 'project_name', 'customer_name', 'offering_name', 'plan_name'],
        'marketplace-orders': ['uuid', 'state', 'type', 'resource_name', 'offering_name', 'project_name', 'created'],
        'roles': ['uuid', 'name', 'description', 'is_active'],
    }

    # Hybrid logic: if Claude didn't request fields, inject essentials
    if 'field' not in payload and method in essential_fields:
        payload['field'] = essential_fields[method]
        logger.info(f"DEBUG: Injected fields! payload['field'] = {payload['field']}")
    else:
        logger.info(f"DEBUG: Did NOT inject fields")

    logger.info(f"DEBUG: payload after injection = {payload}")

    result = await call_waldur_apis(
        WALDUR_API_TOKEN=WALDUR_API_TOKEN,
        method=method, 
        http_method=http_method, 
        arguments=payload,
        max_results=max_results,
        fetch_all_pages=fetch_all_pages,
    )
    return result

# Function to call Waldur APIs with automatic pagination for GET requests
async def call_waldur_apis(
    WALDUR_API_TOKEN: str,
    method: str,
    http_method: str = "GET",
    arguments: dict | None = None,
    max_results: int | None = None,
    fetch_all_pages: bool = False,
):
    """
    Calls Waldur REST API. By default returns the FIRST page only (≤100 rows).
    Set fetch_all_pages=True or max_results=N to fetch more.

    Args:
        WALDUR_API_TOKEN (str)
        method (str): API endpoint (e.g., "customers", "projects", "users")
        http_method (str): only "GET" supported
        arguments (dict | None): query params, e.g. {"name": "Bristol"}
        max_results (int | None): hard cap on rows returned; None = no cap
        fetch_all_pages (bool): if True, paginate to the end (old behaviour).
                                Default False = first page only.

    Returns:
        str: JSON string with returned_count, total_available, truncated flag,
             method, data, and a hint if results were truncated.
    """
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)
    url = WALDUR_BASE_URL + f"{method}/"
    headers = {"Authorization": WALDUR_API_TOKEN}

    args = dict(arguments or {})
    args.setdefault("page_size", 100)

    if max_results is not None:
        cap = max_results
    elif fetch_all_pages:
        cap = None
    else:
        cap = args["page_size"]

    all_data = []
    page = 1
    MAX_PAGES = 10000
    last_response = None

    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        while page <= MAX_PAGES:
            params = {**args, "page": page}
            try:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
            except Exception as e:
                return f"Connection error: {e}"
            last_response = response

            if response.status_code in (200, 201):
                data = response.json()
                if not isinstance(data, list):
                    return f"Unexpected response format: {type(data)}, content: {repr(data)[:100]}"
                if not data:
                    break
                all_data.extend(data)
                if cap is not None and len(all_data) >= cap:
                    all_data = all_data[:cap]
                    break
                if not fetch_all_pages and max_results is None:
                    break
                page += 1
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 404:
                break
            else:
                return f"API error: {response.status_code}."

    total_available = len(all_data)
    if last_response is not None:
        try:
            total_available = int(last_response.headers.get("x-result-count", len(all_data)))
        except (TypeError, ValueError):
            total_available = len(all_data)

    import json
    return json.dumps({
        "returned_count": len(all_data),
        "total_available": total_available,
        "truncated": total_available > len(all_data),
        "method": method,
        "data": all_data,
        "hint": (
            "Showing first page only. Pass max_results=N or fetch_all_pages=True "
            "in parsed_intent for more rows. For statistics across all rows, use "
            "summarise_from_waldur instead (when available)."
        ) if total_available > len(all_data) else None,
    }, indent=2, default=str)