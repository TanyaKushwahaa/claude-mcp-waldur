# src/tools/waldur_get_tools.py
from config import WALDUR_BASE_URL, VERIFY_SSL
from src.mcp_instance import mcp
import httpx

from src.utils import normalise_waldur_token

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
    This MCP tool makes a Waldur API call using the parsed intent, which includes:
    
    parsed_intent should include:
    - WALDUR_API_TOKEN (str)
    - method (str): e.g., 'projects', 'customers', etc.
    - http_method (str): 'GET', 'POST', etc.
    - payload (dict): parameters for the request

    Example input:
    parsed_intent = {
        "WALDUR_API_TOKEN": "Token 2b2b323ki3hinrknfwdwd2322",
        "method": "projects",
        "http_method": "GET",
        "payload": {"short_name": "test"}
    }

    ============================================
    AVOID MISINTERPRETING PROJECT/CUSTOMER NAMES
    ============================================
    If the user's query says:
        "Add user ... to project Scientific Research in Bristol University"
    Then your GET query should be split into:
        1. First check if customer with name "Bristol University" exists:
            {
                "WALDUR_API_TOKEN": "Token 2b2b323ki3hinrknfwdwd2322",
                "method": "customers",
                "http_method": "GET",
                "payload": {"name": "Bristol University"}
            }

        2. Then look for a project with name "Scientific Research":
            {
                "WALDUR_API_TOKEN": "Token 2b2b323ki3hinrknfwdwd2322",
                "method": "projects",
                "http_method": "GET",
                "payload": {"name": "Scientific Research"}
            }

    - DO NOT search for the entire phrase "Scientific Research in Bristol University" as a project name.
    - DO NOT assume the user meant a different customer/project if no exact match is found.

    ======================================
    SYSTEM RESPONSE GUIDELINES
    ======================================
    - If a resource (e.g., customer or project) is not found, elicit clarification.
    - NEVER assume or hallucinate information.
    - ALWAYS explain results in user-friendly language.
    - If tool access fails, apologise and state you are having trouble connecting (do not fabricate an answer).

    Returns:
        str: User-friendly summary or error message from the Waldur API call. 
    """


    WALDUR_API_TOKEN = parsed_intent['WALDUR_API_TOKEN']
    method = parsed_intent['method']
    http_method = parsed_intent['http_method']
    payload = parsed_intent['payload']
    
    result = await call_waldur_apis(
        WALDUR_API_TOKEN=WALDUR_API_TOKEN,
        method=method, 
        http_method=http_method, 
        arguments=payload
    )
    return result

# Function to call Waldur APIs with automatic pagination for GET requests
async def call_waldur_apis(
    WALDUR_API_TOKEN: str,
    method: str, 
    http_method: str = "GET", 
    arguments: dict | None = None
):
    """
    Calls Waldur REST API with automatic pagination for GET requests.
    
    Args:
    - WALDUR_API_TOKEN (str)
    - method (str): API endpoint (e.g., "customers", "projects", "users", etc.)
    - http_method (str): HTTP method to use (only "GET" supported here)
    - arguments (dict | None): Parameters for the GET request, e.g., {"name": "Bristol University"}

    Returns:
    - str: User-friendly summary of all retrieved data or error message.
    """
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)
    url = WALDUR_BASE_URL + f"{method}/"
    headers = {
        "Authorization": WALDUR_API_TOKEN
    }

    all_data = []
    MAX_PAGES = 1000
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        page = 1
        while page<=MAX_PAGES: # to prevent loop going infinitely, if there's any server issue
            if arguments: # Always set "page" from the loop counter, overriding any "page" in arguments
                params = {
                    **arguments, 
                    "page": page
                } 
            else:
                params = {
                    "page": page
                }  # Start with page 1 for pagination
                
            try:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
                if response.status_code in (200, 201):
                    data = response.json()
                    if isinstance(data, list):
                        if len(data) > 0:
                            all_data.extend(data)
                            page += 1
                        else: # Empty list means no more pages
                            break
                    else:
                        return f"Unexpected response format: {type(data)}, content: {repr(data)[:100]}"
                elif response.status_code == 401:
                    return "Authentication failed. Please check your Waldur API token."
                elif response.status_code == 403:
                    return "Access denied. You don't have permission for this operation."
                elif response.status_code == 404: # If the API returns 404, treat it as no more results.
                    break
                else: # Other errors indicate problems
                    return f"Authentication failed. Please check your Waldur API token. Error: {response.status_code}."
            except Exception as e:
                return f"Connection error: {e}"  

    # After fetching all pages, format the results   
    if all_data:
        description = "\n\n".join(["\n".join([f"{k} - {v}" for k, v in item.items()]) for item in all_data])
        return f"Here is the data from Waldur for {method}:\n\n{description}."
    else:
        return f"No data found for {method}."        