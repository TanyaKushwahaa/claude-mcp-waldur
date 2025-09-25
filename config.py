from src.mcp_instance import mcp
import environ

env = environ.Env(
    WALDUR_BASE_URL=(str, ''),           # (type, default_if_missing)
    MCP_DATA_PATH=(str, ''),
    VERIFY_SSL=(bool, False),            # This will properly convert "False" string to False boolean
    CLIENT_ID=(str, ''),
    DISCOVERY_URL=(str, ''),
    TOKEN_ENDPOINT=(str, ''),
    DEVICE_ENDPOINT=(str, '')
)
# This line reads the .env file
environ.Env.read_env()

WALDUR_BASE_URL = env("WALDUR_BASE_URL")
MCP_DATA_PATH = env("MCP_DATA_PATH")
CLIENT_ID = env("CLIENT_ID")
DISCOVERY_URL = env("DISCOVERY_URL")
DEVICE_ENDPOINT = env("DEVICE_ENDPOINT")
TOKEN_ENDPOINT = env("TOKEN_ENDPOINT")
VERIFY_SSL=env("VERIFY_SSL")

def validate_config():
    missing = []
    if not WALDUR_BASE_URL:
        missing.append("WALDUR_BASE_URL")
    if not CLIENT_ID:
        missing.append("CLIENT_ID")
    if not DISCOVERY_URL:
        missing.append("DISCOVERY_URL")
    if not TOKEN_ENDPOINT:
        missing.append("TOKEN_ENDPOINT")
    if not DEVICE_ENDPOINT:
        missing.append("DEVICE_ENDPOINT")
    if missing:
        return f"Missing environment variables: {', '.join(missing)}"
    return None