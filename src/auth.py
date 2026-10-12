"""
МОДУЛЬ АВТОРИЗАЦИИ (src/auth.py)
--------------------------------
Проверяет Bearer-токен клиента при работе по HTTP.
Токен задаётся переменной окружения MCP_BEARER_TOKEN.
"""

import secrets
from typing import Optional

from mcp.server.auth.provider import AccessToken


class StaticBearerTokenVerifier:
    """Сверяет токен клиента с одним токеном из настроек, не логируя его."""

    def __init__(self, expected_token: str) -> None:
        self._expected_token = expected_token

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        if not secrets.compare_digest(token, self._expected_token):
            return None
        return AccessToken(
            token=token,
            client_id="formspree-mcp-client",
            scopes=["formspree:read"],
        )
