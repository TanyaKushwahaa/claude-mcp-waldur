# src/tools/waldur_auth_tool.py

# MCP tool to handle Waldur authentication via Keycloak OIDC device authorisation flow.
# - Requests device code and displays verification URL + code to the user
# - Prompts the user to authorise in their browser and provide OIDC token (no polling)
# - Exchanges OIDC token for a Waldur API token via Waldur OpenPortal get_API_token
# - Returns Waldur API token, user email, and access level (staff/read-only)
# - Automatically handles expired/invalid tokens and clears session
"""## Security Note
This tool uses shared OAuth2 client credentials to authenticate with Keycloak as an application. Individual user authentication happens securely via the device authorisation flow. 
Each user receives their own unique API token."""

import time
import os
import httpx
from dotenv import load_dotenv
from src.mcp_instance import mcp
from config import WALDUR_BASE_URL, VERIFY_SSL

load_dotenv()

# Global dictionary to persist device authorisation session across calls
DEVICE_SESSION={}

@mcp.tool()
async def get_waldur_api_token(authorised: str | None) -> str | dict:
    """
    MCP tool to obtain Waldur API token using device authorisation flow.
    
    Steps:
    1. Request device code from Keycloak.
    2. Show user verification URL and code.
    3. Prompt user to complete authorise in browser and confirm when done.
    4. Exchange completed device authorisation for Waldur API token.
    Args: 
        authorised (str | None) : "yes" or "no" ONLY. 
            - Use "no" initially (user not authorised yet).
            - Use "yes" once the user has completed the browser authorisation process.
    Returns:
        str: Waldur API token with user role infomration, OR
        dict: elicitation object prompting the user to authorise.
    Note:
        The raw token is not shown to the user; only the result of authorisation is displayed.
    """

# -----------------
    global DEVICE_SESSION

    client_id = "homeport-public"
    discovery_url = "https://keycloak-dev.isambard.ac.uk/realms/isambard/.well-known/openid-configuration"
    device_endpoint = "https://keycloak-dev.isambard.ac.uk/realms/isambard/protocol/openid-connect/auth/device"
    token_endpoint = "https://keycloak-dev.isambard.ac.uk/realms/isambard/protocol/openid-connect/token"
    
    if discovery_url:
        discovery_url_response = httpx.get(
        discovery_url,
        timeout=5.0)
        data_discovery_url = discovery_url_response.json()
        device_endpoint = data_discovery_url["device_authorization_endpoint"]
        token_endpoint = data_discovery_url["token_endpoint"]
    else:
        return "Discovery URL does not exist."

    if not DEVICE_SESSION:
        # Step 1: Request device code
        data_for_device_auth = {
            "client_id":client_id,
            # "client_secret":client_secret,
            "scope": "openid profile email"
        }
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            device_response = await client.post(device_endpoint, data=data_for_device_auth, timeout=10.0)
            if device_response.status_code==200:
                device_data=device_response.json()
                DEVICE_SESSION={
                    "verification_uri": device_data['verification_uri'],
                    "user_code": device_data['user_code'],
                    "device_code": device_data['device_code'],
                    "expires_in": device_data['expires_in']
                }
            else: 
                return f"Failed to get device code: {device_response.status_code}"

    verification_uri = DEVICE_SESSION["verification_uri"]
    user_code = DEVICE_SESSION["user_code"]
    device_code = DEVICE_SESSION["device_code"]
    expires_in = DEVICE_SESSION["expires_in"]

    data_for_token = {
    "grant_type":"urn:ietf:params:oauth:grant-type:device_code",
    "device_code":device_code,
    "client_id":client_id,
    # "client_secret":client_secret
}

    # Step 2: If authorised is "yes", do a single check first, then use the supplied OIDC token
    if authorised and authorised.lower()=="yes":
        # Do a quick check to see if authorisation is ready
        async with httpx.AsyncClient(verify=VERIFY_SSL) as client:
            quick_check = await client.post(token_endpoint, data=data_for_token, timeout=10.0)
            if quick_check.status_code==400:
                # User hasn't authorised yet
                return {
                    "type":"elicitation/create",
                    "params":{
                        "message": (
                            "You haven't completed authorisation yet. "
                            f"Please visit {verification_uri} and enter code {user_code}. "
                            "Then try again with 'yes'."
                        ),
                        "requestedSchema": {
                            "type":"object",
                            "properties": {
                                "retry": {
                                    "type": "string",
                                    "description": "Type 'yes' after completing authorisation",
                                }
                            },
                            "required": ["retry"],
                        },
                    },
                }
            
            elif quick_check.status_code==200:
                # Authorisation successful!
                token = quick_check.json()
                OIDC_TOKEN = token["access_token"]
                DEVICE_SESSION = {} # clear session for next authorisation
            else:
                DEVICE_SESSION = {} # clear so any data from previous authorisation is cleared
                return f"Authorization error: {quick_check.status_code}, {quick_check.text}."
    
    # Step 3: If not authorised, return elicitation prompt to the user
    else:
        return {"type":"elicitation/create",
                "params":{
                    "message": (
                        f"Please authorise yourself in your browser."
                        f"Visit {verification_uri} \n"
                        f"Enter code {user_code} \n"
                        "The tool will automatically receive your OIDC token once authorised."
                    ),
                    "requestedSchema": {
                        "type":"object",
                        "properties": {
                            "OIDC_TOKEN": {
                                "type": "string",
                                "description": "OIDC token for device authorisation",
                            }
                        },
                        "required": ["OIDC_TOKEN"],
                        },
                    },
                }

    # Step 4: Exchange OIDC token for Waldur API token
    url = WALDUR_BASE_URL + "openportal/get_API_token/"
    headers = {
        "Authorization": f"Bearer {OIDC_TOKEN}"
    }

    async with httpx.AsyncClient(follow_redirects = True, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json()
                token = data["token"]
                user_access = data["user_access"]
                user_email = data["user_email"]
                if user_access=="staff":
                    result = f"Successfully authorised! You are a staff user. Token {data['token']} and Email {user_email}."
                    # result = f"Successfully authorised! You are a staff user. Token {data["token"]}."
                else:
                    result = f"Successfully authorised! But you have read-only access. Token {data['token']} and Email {user_email}."
            elif response.status_code==401:
                result = "Invalid token."
            else:
                result = f"Unexpected error: {response.status_code}"
            return result
        except Exception as e:
            return f"Trouble connecting to the server: {e}"