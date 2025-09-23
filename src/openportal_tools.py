# src/tools/user_tools.py

"""
User-related tools for interacting with Waldur APIs.

Each tool has its own rules, required arguments, and response expectations.
These rules are written in the docstrings so the LLM knows how to use them
safely and consistently.
"""

import httpx
from dotenv import load_dotenv
from src.mcp_instance import mcp
from config import WALDUR_BASE_URL, VERIFY_SSL

from src.utils import normalise_waldur_token

load_dotenv()

@mcp.tool()
async def get_project_short_name(WALDUR_API_TOKEN: str, project_name: str, customer_name: str) -> str:
    """
    Retrieve the short name of a project.   

    RULES:
    - Use ONLY the given endpoint ("project_short_name").
    - DO NOT try to fetch project data by any other means.
    - Keep responses short and relevant.

    Args:
        WALDUR_API_TOKEN (str): Waldur API token.
        project_name (str): Project name (e.g., "Maths research").
        customer_name (str): Customer/organization name (e.g., "Bangor University").

    Returns:
        str: Project short name or error message.
    """
    
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)  
    url = WALDUR_BASE_URL + "openportal/project_short_name/"
    headers = {
        "Authorization": WALDUR_API_TOKEN,
        "Content-Type":"application/json"
    }
    params = {
        "project_name": project_name, 
        "customer_name": customer_name
    }

    async with httpx.AsyncClient(follow_redirects = True, verify = VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json()
                return (f"Here is the shortname of the project {project_name}" 
                          f"in the organization {customer_name}: {list(data.values())}.")
            elif response.status_code==401:
                return "Authentication failed. Please check your Waldur API token."
            else:
                return f"The project '{project_name}' or customer '{customer_name}' does not exist."
        except Exception as e:
            return f"Trouble connecting to the server: {e}"
        
@mcp.tool()
async def get_customer_spend_info(WALDUR_API_TOKEN: str, customer: str | None = None)-> str | dict:
    """
    MCP tool to retrieve customer spending information from Waldur.

    RULES:
    - If customer is missing, request it from the user via elicitation.
    - Use ONLY the given endpoint (`customer_spend_info`).
    - DO NOT try to fetch customer data by any other means.
    - Keep responses short and relevant.

    Args:
        WALDUR_API_TOKEN (str): Waldur API token.
        customer (str | None): Customer name (e.g., "Bristol University").

    Returns:
        dict | str: Customer spend info or elicitation message.
    """

    if not customer:
        return {"type":"elicitation/create",
                "params":{
                    "message": "Which customer would you like spending info for?",
                    "requestedSchema": {
                        "type":"object",
                        "properties": {
                            "customer": {
                                "type": "string",
                                "description": "The name of the customer or institution (e.g., ABC University)",
                            }
                        },
                        "required": ["customer"]
                    },
                },
            }
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)  
    url = WALDUR_BASE_URL + "openportal/customer_spend_info/"
    headers = {
        "Authorization": WALDUR_API_TOKEN
    }
    params = {
        "customer":customer
    }
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.)
            if response.status_code in (200, 201):
                return response.json()
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 404:
                return f"Customer '{customer}' not found."
            else:
                return f"API returned status error: {response.status_code}."
        except Exception as e:
            return f"Problem connecting to the server. Please try again later. Error: {e}"

@mcp.tool()
async def get_user_info(WALDUR_API_TOKEN, email):
    """
    Retrieve user information in a human-friendly format.

    RULES:
    - Use ONLY the given URL endpoint ("whoami").
    - DO NOT try to fetch user data by any other means.
    - DO NOT provide more information than what this tool returns.
    - Keep responses short and relevant.
    
    Args:
        WALDUR_API_TOKEN (str): Waldur API token.
        email (str): Email (e.g., "nd@example.com").    
    
    Returns:
        str: User information or error message.
    """
    if not WALDUR_API_TOKEN:
        return "Missing Waldur API token."
    if not email:
        return "Missing required parameter: email."
    
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)  
    url = WALDUR_BASE_URL + "openportal/whoami/"
    headers = {
        "Authorization": WALDUR_API_TOKEN,
        "Content-Type":"application/json"
    }
    params = {
        "email": email
    }

    async with httpx.AsyncClient(follow_redirects = True, verify = VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json()
                return f"Here is the user information: {data}."
            elif response.status_code == 401:
                return "Authentication failed. Please check your Waldur API token."
            elif response.status_code == 403:
                return "Access denied. You don't have permission for this operation."
            elif response.status_code == 404:
                return "Resource not found."
            else:
                return f"API returned status error: {response.status_code}."
        except Exception as e:
            return f"Trouble connecting to the server: {e}"
        
@mcp.tool()
async def get_project_users(WALDUR_API_TOKEN, project_name):
    """
    Retrieve information about users in a given project.

    RULES:
    - Use ONLY the given URL endpoint ("list_project_users").
    - DO NOT try to fetch project membership by any other means.
    - DO NOT provide more information than what this tool returns.
    - Keep responses short and relevant.

    Args:
        WALDUR_API_TOKEN (str): Waldur API token.
        project_name (str): Project name (e.g., "Maths research").

    Returns:
            str: Project user information or error message.
    """
    if not WALDUR_API_TOKEN:
        return "Missing Waldur API token."
    if not project_name:
        return "Missing required parameter: project name."
    
    # Add "Token " if it does not exist
    WALDUR_API_TOKEN = normalise_waldur_token(WALDUR_API_TOKEN)    
    url = WALDUR_BASE_URL + "openportal/list_project_users/"
    headers = {"Authorization": WALDUR_API_TOKEN,"Content-Type":"application/json"}
    params = {"project_name": project_name}

    async with httpx.AsyncClient(follow_redirects = True, verify = VERIFY_SSL) as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=10.0)
            if response.status_code in (200, 201):
                data = response.json()
                return f"Here is the project users information: {data}."
            elif response.status_code == 401:
                return "Invalid token."
            return f"Authentication failed. Please check your Waldur API token. Error: {response.status_code}."
        except Exception as e:
            return f"Trouble connecting to the server: {e}"
