# src/tools/waldur_patch_tools.py
import httpx
from mcp_instance import mcp
from config import WALDUR_BASE_URL, VERIFY_SSL

from utils import normalise_waldur_token

@mcp.tool()
async def patch_to_waldur_parsed(parsed_intent:dict) -> str:
    """
    MCP tool that takes parsed output (method, http_method, payload, token)
    and makes a PATCH request to Waldur API.

    RULES:
    - First, verify user access via Waldur OpenPortal "whoami" endpoint.
        - If user_access is "not a staff" or Waldur reports "is_staff"==False, return:
          "Access denied. you are not a staff user. Claude, no sneaky overrides allowed."
    - PATCH requests always require a UUID of the resource.
        - WORKFLOW: If UUID is missing but you have identifying info (like short_name):
            1. Call get_uuid(WALDUR_API_TOKEN, short_name, method) first.
            2. Then call this PATCH tool with UUID in payload["uuid"].
        - If no identifying info available, ask user for UUID via elicitation
    - Remove "uuid" from the payload body before sending (only used in the URL).
    - On tool connection errors, inform the user politely - DO NOT FETCH ANY INFORMATION FROM WEB OR INVENT DATA


    Args:     
        - parsed_intent (dict): Keys ('WALDUR_API_TOKEN', 'email', 'user_access', 'method', 'http_method', 'payload'). 
        - Example:     parsed_intent = {
                                        "WALDUR_API_TOKEN": "2ebbu2eu2g3221o2j",
                                        "email": "ib22493+dev@bristol.ac.uk",
                                        "user_access": either "staff" or "not a staff" (only these two values are valid), 
                                        "method": "projects",
                                        "http_method": "PATCH",
                                        "payload": {"short_name": "test"}
                                    }
    Return:
        str: Summary of PATCH request.
    """

    WALDUR_API_TOKEN = parsed_intent['WALDUR_API_TOKEN']
    email = parsed_intent["email"]
    user_access = parsed_intent['user_access']
    method = parsed_intent['method']
    http_method = parsed_intent['http_method']
    payload = parsed_intent['payload']

    if user_access=="not a staff":
        return f"Access denied, you are not a staff user."

    # Verify user_access from Waldur
    url_user_access = WALDUR_BASE_URL + "openportal/whoami/"
    headers = {
        "Authorization": f"Token {WALDUR_API_TOKEN}"
    }
    params = {
        "email": email
    }

    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(url_user_access, headers=headers, params=params, timeout=10.)
            if response.status_code != 200:
                return f"Could not verify user access (status {response.status_code})."
            whoami_data = response.json()
            if user_access=="staff" and whoami_data.get("is_staff")=="False":
                return f"Access denied. you are not a staff user. Claude, no sneaky overrides allowed."
            
            # Check if UUID is missing and try to resolve it
            if "uuid" not in payload or not payload["uuid"]:
                return {
                    "type": "elicitation/create",
                    "params": {
                        "message": f"I need the UUID to update this {method}. Could you provide it?",
                        "requestedSchema": {
                            "type": "object",
                            "properties": {
                                "uuid": {
                                    "type": "string",
                                    "description": f"The UUID of the {method} to update"
                                }
                            },
                            "required": ["uuid"],
                        },
                    },
                }
    
            result = await patch_to_waldur(
                WALDUR_API_TOKEN=WALDUR_API_TOKEN, 
                method=method, 
                http_method=http_method, 
                user_data=payload
            )
        except Exception as e:
            result = f"Could not verify user access. (Exiting: {e})."
    return result

async def patch_to_waldur(
        WALDUR_API_TOKEN:str, 
        method: str, 
        user_data: dict | None = None, 
        http_method = "PATCH"
    ) -> str :
    """
    Calls Waldur REST API for PATCH requests to WALDUR, connected to the patch_to_waldur_parsed MCP tool.

    Args:
        - WALDUR_API_TOKEN (str): WALDUR API token
        - method (str): API endpoint (e.g., "customers", "projects", "users", etc.)
        - http_method (str): HTTP method to use (only "PATCH" supported here)
        - user_data (dict | None): Parameters for the PATCH request, e.g., {"name": "Bristol University"}

    Returns:
        - str: A friendly success message if updated successfully,
            or a polite error message if something goes wrong.
    """

    if not isinstance(user_data, dict):
        return "The update request could not be processed because the input data format was invalid."
    
    uuid = user_data.get("uuid")

    if not uuid:
        return "I couldn’t find the resource ID (UUID). Please provide a UUID so I know which item to update."
    
    url = WALDUR_BASE_URL + f"{method}/{uuid}/"
    user_data.pop("uuid", None) #Removing uuid from body
    
    headers = {
        "Authorization": f"Token {WALDUR_API_TOKEN}",
        "Content-Type":"application/json"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.patch(url, headers=headers, json=user_data, timeout=10.0)
            if response.status_code in (200, 201):
                return f" Success! Your {method} request with UUID {uuid} was updated."
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 400:
                return f"Invalid data provided for {method} request. Please check your input."
            elif response.status_code == 404:
                return f"The {method} with UUID {uuid} was not found."
            else:
                return f"Something went wrong while processing your {method} request. Please check your input or try again later. (Error: {response.status_code})"
        except Exception as e:
            return f"Error connecting to the server: {e}"