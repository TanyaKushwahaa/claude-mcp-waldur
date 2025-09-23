def normalise_waldur_token(token: str) -> str:
    """
    Normalise Waldur API token to proper format.
    Args:
        token: Raw token or token with 'Token ' prefix
    Returns:
        Token formatted for Authorization header
    """
    if token.startswith("Token "):
        return token
    return f"Token {token}"