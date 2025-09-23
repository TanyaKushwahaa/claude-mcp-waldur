# src/tools/misc_tools.py

"""
Miscellaneous tools for interacting with Waldur APIs.

Each tool has its own rules, required arguments, and response expectations.
These rules are written in the docstrings so the LLM knows how to use them
safely and consistently.
"""

import httpx
import logging
from src.mcp_instance import mcp
from config import WALDUR_BASE_URL, VERIFY_SSL

from src.utils import normalise_waldur_token

@mcp.tool()
async def infer_http_method(query: str) -> dict:
    """
    Infer the HTTP method (GET, POST, PATCH, DELETE) from the user's query.

    RULES:
    - Use POST for create, add, submit, post, invite, new.
    - Use PATCH for update, edit, modify, change.
    - Use DELETE for delete, remove.
    - Use GET for get, list, retrieve, show.

    Args:
        query (str): User query text.

    Returns:
        dict: {"method": "HTTP_METHOD"} or {"error": "error_message"}.
    """
    try:
        logging.info(f"Received query: {query}")

        if not query:
            return {"error": "Empty query provided."}
        query = query.lower()

        if any(word in query for word in ['create', 'add', 'submit','post', 'new', 'invite']):
            return {"method": "POST"}
        elif any(word in query for word in ['update', 'edit', 'modify', 'patch', 'change']):
            return {"method": "PATCH"}
        elif any(word in query for word in ['delete', 'remove']):
            return {"method": "DELETE"}
        elif any(word in query for word in ['get', 'list', 'retrieve', 'show']):
            return {"method": "GET"}
        
        return {"error": "Could not infer HTTP method from query."}
    
    except Exception as e:
        logging.error(f"Error in infer_hhtp_method: {str(e)}")
        return {"error": f"Processing error: {str(e)}"}
    

@mcp.tool()
def greet_user(user_query: str) -> dict:
    """
    Greet the user happily and clarify their intent.

    RULES:
    - Always greet with a positive tone.
    - Rephrase the query to confirm user intent.
    - Ask the user for confirmation via elicitation.

    Args:
        user_query (str): Raw user query.

    Returns:
        dict: Elicitation message with confirmation schema.
    """

    
    return {"type":"elicitation/create",
            "params":{
                "message": f"Hello! I'm here to help. \n Just to confirm: is your query about - "
                f"'{user_query}'?",
                "requestedSchema": {
                    "type":"object",
                    "properties": {
                        "confirm": {
                            "type": "string",
                            "description": "Please type 'Yes' to confirm or 'No' to correct it."
                        }
                    },
                    "required": ["confirm"],
                    },
                },
            }


@mcp.tool()
async def check_query_type(query_type: str | None = None) -> dict:
    """
    MCP tool to ask whether their query requires READ-ONLY or READ-WRITE access.
    
    RULES:
    - If query_type is missing, elicit it from the user.
    - Accept only exact values: "READ-ONLY" or "READ-WRITE".
    - Reject invalid choices with a polite error.
    
    Args: 
        - query_type (str | None): Optional query type.
    Returns:
        dict: Elicitation or query type confirmation.
    """

    if not query_type:
        return {"type":"elicitation/create",
        "params":{
            "message": "Is your query READ-ONLY or READ-WRITE?\n"
            "Please type exactly READ-ONLY or READ-WRITE",
            "requestedSchema": {
                "type":"object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "description": "Query type (e.g., READ-ONLY)"
                    }
                },
                "required": ["query_type"]
                }
            }
        }
    if query_type not in ("READ-ONLY", "READ-WRITE"):
        return {"error": "Invalid choice. Please type READ-ONLY or READ-WRITE."}
    return {"query_type": query_type}

@mcp.tool()
async def invite_user(WALDUR_API_TOKEN: str, parsed_intent:dict) -> str | dict:
    """
    Send a user invitation via Waldur's "user_invitations" API.

    RULES:
    - If 'role' is missing:
        - WORKFLOW:
            1. Call get_from_waldur with method="roles" to fetch available roles
            2. Present roles to user via elicitation 
            3. Call this invite_user tool again with the selected role UUID
            - DO NOT assume or auto-assign (e.g., if the user says add Jack as project member, fetch only the "member" role, do not pick admin etc.).
    - On connection errors, inform the user politely.
    - DO NOT FETCH ANY INFORMATION FROM THE WEB OR INVENT DATA.

    Args: 
        WALDUR_API_TOKEN (str): Waldur API token.
        parsed_intent (dict): Must include a payload with required keys: 
            - role (UUID str) 
            - scope (str) 
            - email (str)
        Optional keys:  
            full_name, native_name, phone_number, organization, 
            job_title, civil_number, extra_invitation_text.

    Returns: 
        str: Invitation status or elicitation message.
    """

    if not WALDUR_API_TOKEN:
        return "Missing Waldur API token."

    method = "user-invitations"
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)
    url = WALDUR_BASE_URL + f"{method}/"
    payload  = parsed_intent['payload']

    headers = {
        "Authorization": WALDUR_API_TOKEN,
        "Content-Type":"application/json"
    }
    if "role" not in payload or not payload['role']:
        return {"type":"elicitation/create",
        "params":{
            "message": "Which role do you want to assign to the user?",
            "requestedSchema": {
                "type":"object",
                "properties": {
                    "role": {
                        "type": "string",
                        "description": "Available roles from Waldur (e.g., PROJECT.ADMIN UUID).",
                    }
                },
                "required": ["role"],
                }
            }
        }
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.post(url, headers = headers, json=payload, timeout=10.0)
            if response.status_code in (200, 201):
                return "Invitation sent successfully! The user will receive an email."
                # Log the response.text for internal debugging only
                # logger.warning(f"Waldur error {response.status_code}: {response.text}")
            return f"Something went wrong while sending the invitation. Please check your input or try again later. (Error code: {response.status_code})"
        except Exception as e:
            return f"I'm having trouble connecting to the server right now. Please try again later. Error: {e}"