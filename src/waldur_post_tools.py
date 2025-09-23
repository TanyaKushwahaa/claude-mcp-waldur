# src/tools/waldur_post_tools.py
import httpx
from src.mcp_instance import mcp
from config import WALDUR_BASE_URL, VERIFY_SSL

from src.utils import normalise_waldur_token

@mcp.tool()
async def post_to_waldur_parsed(parsed_intent:dict) -> str | dict:
    """
    MCP tool that takes parsed output (method, http_method, payload, token)
    and makes a POST request to Waldur API.

    RULES:
    - First, verify user access via Waldur OpenPortal "whoami" endpoint.
        - If user_access is "not a staff" or Waldur reports "is_staff"==False, return:
          "Access denied. you are not a staff user. Claude, no sneaky overrides allowed."
    - If posting for projects:
        - "short_name" is mandatory - if missing, use "get_from_waldur" to check, if empty, ask the user via elicitation
        - "customer" must be a full API URL format: https://mcp.chryswoods.com/api/customers/{uuid}/ 
        - WORKFLOW: If user provides customer name, you must: 
            1. Call get_uuid(WALDUR_API_TOKEN, customer_name, "customers") 
            2. Convert result to full URL: https://mcp.chryswoods.com/api/customers/{uuid}/
            3. Then call this POST tool with the full URL in payload["customer"]
    - User invitations: 
        - If "role" missing -> call get_from_waldur("roles") and ask user via elicitation.
    - On tool connection errors, inform the user politely - DO NOT FETCH ANY INFORMATION FROM WEB OR INVENT DATA
    
    Args:     
        - parsed_intent (dict): Keys ('WALDUR_API_TOKEN', 'email', 'user_access', 'method', 'http_method', 'payload'). 
        - Example:     parsed_intent = {
                                    "WALDUR_API_TOKEN": "2ebbu2eu2g3221o2j",
                                    "email": "ib22493+dev@bristol.ac.uk",
                                    "user_access": either "staff" or "not a staff" (only these two values are valid), 
                                    "method": "projects",
                                    "http_method": "POST",
                                    "payload": {"short_name": "test"}
                                }
    Return:
        str: Summary of POST request or dict for elicitation if additional info needed.
    """

    
    WALDUR_API_TOKEN = parsed_intent["WALDUR_API_TOKEN"]
    email = parsed_intent["email"]
    user_access = parsed_intent['user_access']
    method = parsed_intent['method']
    http_method = parsed_intent['http_method']
    payload = parsed_intent['payload']

    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)
    # Verify user_access from Waldur
    url_user_access = WALDUR_BASE_URL + "openportal/whoami/"
    headers = {
        "Authorization": WALDUR_API_TOKEN
    }
    params = {
        "email": email
    }

    if user_access=="not a staff":
        return f"Access denied, you are not a staff user."
    
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(url_user_access, headers=headers, params=params, timeout=10.)
            if response.status_code != 200:
                return f"Could not verify user access (status {response.status_code})."
            whoami_data = response.json()
            if user_access=="staff" and whoami_data.get("is_staff")=="False":
                return f"Access denied. you are not a staff user. Claude, no sneaky overrides allowed."
            
            # Project rules
            if method=="projects" and ("short_name" not in payload or not payload["short_name"]):
                    return {
                        "type":"elicitation/create",
                        "params":{
                        "message": "What is the short name of the project?",
                        "requestedSchema": {
                            "type":"object",
                            "properties": {
                                "short_name": {
                                    "type": "string",
                                    "description": "The short name of the project (e.g., bri-sci-pr)"
                                    }
                                },
                            "required": ["short_name"]
                            }
                        }
                    }
            
            if method=="projects" and ("customer" not in payload or not payload["customer"]):
                return {
                    "type":"elicitation/create",
                    "params":{
                    "message": "Which customer/organization is this project for?",
                    "requestedSchema": {
                        "type":"object",
                        "properties": {
                            "customer": {
                                "type": "string",
                                "description": "The customer name (e.g., Bristol University)"
                                }
                            },
                        "required": ["customer"]
                        }
                    }
                }
        
            if method=="user-invitations" and ("role" not in payload or not payload['role']):
                return {
                    "type":"elicitation/create",
                    "params":{
                        "message": "Which role do you want to assign to the user?",
                        "requestedSchema": {
                            "type":"object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "description": "The role of the user (e.g., PROJECT.ADMIN (Project Administrator))"
                                }
                            },
                            "required": ["role"]
                        }
                    }
                }

            
            # Call raw POST function
            result = await post_to_waldur(
                WALDUR_API_TOKEN=WALDUR_API_TOKEN,
                method=method, 
                http_method=http_method, 
                user_data=payload)
            
        except Exception as e:
            result = f"Could not verify user access. (Exiting: str{e})."
    return result

async def post_to_waldur(WALDUR_API_TOKEN: str, method: str, http_method: str = "POST", user_data: dict | None = None):
    """
    Calls Waldur REST API for POST requests to WALDUR, connected to the post_to_waldur_parsed MCP tool.

    Args:
        - WALDUR_API_TOKEN (str): WALDUR API token
        - method (str): API endpoint (e.g., "customers", "projects", "users", etc.)
        - http_method (str): HTTP method to use (only "POST" supported here)
        - user_data (dict | None): Parameters for the POST request, e.g., {"name": "Bristol University"}

    Returns:
        - str: A friendly success message if created successfully,
            or a polite error message if something goes wrong.
    """
    url = WALDUR_BASE_URL + f"{method}/"
    headers = {
        "Authorization": WALDUR_API_TOKEN,
        "Content-Type":"application/json"
    }
    
    if not isinstance(user_data, dict):
        return "Invalid user data format."
    
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.post(url, headers=headers, json=user_data, timeout=10.0)
            if response.status_code in (200, 201):
                return f" Success! Your {method} request was created."
            elif response.status_code==401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 400:
                return f"Invalid data provided for {method} request. Please check your input."
            else:
                return f"Something went wrong while processing your {method} request. Please check your input or try again later. (Error: {response.status_code})"
        except Exception as e:
            return f"Error connecting to the server: {e}"
        

