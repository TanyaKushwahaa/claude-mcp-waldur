# src/tools/waldur_delete_tools.py
from config import WALDUR_BASE_URL, VERIFY_SSL
from mcp_instance import mcp
import httpx

from utils import normalise_waldur_token

@mcp.tool()
async def delete_from_waldur_parsed(parsed_intent:dict, confirm: str | None) -> str | dict:
    """
    MCP tool that deletes a resource from Waldur using parsed intent (method, http_method, payload).
    
    RULES:
    - First, verify user access via Waldur OpenPortal "whoami" endpoint.
        - If user_access is "not a staff" or Waldur reports "is_staff" == False, return:
          "Access denied. you are not a staff user. Claude, no sneaky overrides allowed."
    - DELETE requests always require a UUID of the resource.
        - WORKFLOW:
            1. Ask user for short_name via elicitation
            2. Call get_uuid(WALDUR_API_TOKEN, short_name, method) to get UUID  
            3. Call this DELETE tool again with UUID in payload
        - If no identifying info available, ask user for UUID directly
    - Before executing deletion, confirm with the user ("Yes" or "No").
    - On tool connection errors, inform the user politely – DO NOT FETCH ANY INFORMATION FROM THE WEB OR INVENT DATA.


    Args: 
        - parsed_intent (dict): Keys ('WALDUR_API_TOKEN', 'email', 'user_access', 'method', 'http_method', 'payload'). 
        - Example: 
                parsed_intent = {
                            "WALDUR_API_TOKEN": "2ebbu2eu2g3221o2j",
                            "email": "ib22493+dev@bristol.ac.uk",
                            "user_access": either "staff" or "not a staff" (only these two values are valid), 
                            "method": "projects",
                            "http_method": "DELETE",
                            "payload": {"short_name": "test"}
                        }
    Return:
        str | dict: A summary of the DELETE request result, or an elicitation request if more information/confirmation is needed.

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
                
                uuid = payload.get("uuid")
                if not uuid:
                    short_name = payload.get("short_name")
                    if not short_name:
                        return {"type":"elicitation/create",
                            "params":{
                                "message": f"Please provide the short name.",
                                "requestedSchema": {
                                    "type":"object",
                                    "properties": {
                                        "short_name": {
                                            "type": "string",
                                            "description": "The short name (e.g., if it's a project bri-sci-pro)"
                                        }
                                    },
                                    "required": ["short_name"],
                                    },
                                },
                            }
                    
                if uuid and confirm == None :
                    return {"type":"elicitation/create",
                        "params":{
                            "message": f"Are you sure you want to go ahead with deletion?.",
                            "requestedSchema": {
                                "type":"object",
                                "properties": {
                                    "confirm": {
                                        "type": "string",
                                        "description": f"Say Yes or No whether you want to go ahead with deletion of uuid {uuid}"
                                    }
                                },
                                "required": ["confirm"],
                                },
                            },
                        }
                
                if confirm == "Yes" or confirm == "yes":
                    result = await delete_from_waldur(WALDUR_API_TOKEN = WALDUR_API_TOKEN,method=method, uuid=uuid) 
                elif confirm == "No" or confirm == "no":
                    result = "Deletion cancelled as per your request."
                else:
                    result = {"type":"elicitation/create",
                        "params":{
                            "message": f"Are you sure you want to go ahead with deletion?.",
                            "requestedSchema": {
                                "type":"object",
                                "properties": {
                                    "confirm": {
                                        "type": "string",
                                        "description": f"Say Yes or No whether you want to go ahead with deletion of uuid {uuid}"
                                    }
                                },
                                "required": ["confirm"],
                                },
                            },
                        }
            except Exception as e:
                result = f"Could not verify user access. (Exiting: {e})."
    return result


async def delete_from_waldur(WALDUR_API_TOKEN: str, method: str, uuid: str) -> str:
    """
    Calls Waldur REST API for DELETE requests to WALDUR, connected to the delete_from_waldur_parsed MCP tool.
    
    Args:
        - WALDUR_API_TOKEN (str): WALDUR API token
        - method (str): API endpoint (e.g., "customers", "projects", "users", etc.)
        - uuid (str): UUID of the resource to delete

    Returns:
        - str: A friendly success message if updated successfully,
            or a polite error message if something goes wrong.
    """

    url = WALDUR_BASE_URL + f"{method}/{uuid}/"
    
    headers = {
        "Authorization": f"Token {WALDUR_API_TOKEN}",
        "Content-Type":"application/json"
    }
    
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.delete(url, headers=headers, timeout=10.0)
            
            if response.status_code in (204, 202):
                return f"Success! The {method} with the UUID {uuid} was deleted."
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 404:
                return  f"The {method} with UUID {uuid} was not found."
            return f"Couldn't delete the {method} with the UUID {uuid}. {response.status_code} - {response.text}"
        except Exception as e:
            return f"Trouble connecting to the server. Error: {e}"
