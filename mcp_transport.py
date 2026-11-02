# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Magnus Kolsjö
"""Uppstart och transportval för MCP-servern: stdio eller http.

stdio och http är symmetriska val. stdio passar en lokal MCP-klient, där
klienten startar processen direkt. http passar delad drift bakom en
reverse proxy, där en serverprocess betjänar flera klienter.

http-läget är fail-closed: det kräver antingen MCP_API_KEY eller ett
uttryckligt öppet läsläge (MCP_OPPEN_LASNING=på). Utan något av dem avbryts
uppstarten med exitkod 2, så att en öppen endpoint aldrig uppstår av misstag.
Öppet läge är avsett för servrar där alla verktyg bara läser publikt
material. stdio-läget berörs aldrig av autentiseringen.

Bakom en reverse proxy kommer anropen med proxyns Host-huvud, till exempel
mcp.fornmed.se. MCP-biblioteket släpper bara igenom localhost när servern
lyssnar på 127.0.0.1, så de publika namnen anges i MCP_TILLATNA_VARDAR.

Modulen läser inte .env. Servern gör det själv innan den importerar sin
konfiguration, eftersom servern inte ärver shell-miljön från klienten.

Miljövariabler:
    MCP_TRANSPORT        stdio | http                   (standard: stdio)
    MCP_HOST             adress i http-läget            (standard: 127.0.0.1)
    MCP_PORT             port i http-läget              (standard: serverns egen)
    MCP_API_KEY          Bearer-nyckel i http-läget
    MCP_OPPEN_LASNING    på = http-läget utan nyckel    (standard: av)
    MCP_TILLATNA_VARDAR  kommaseparerade värdnamn bakom proxyn, t.ex. mcp.fornmed.se

Ingångspunkter:
    starta(mcp, standardport, initiera=None, forvarm_http=None) -> None
    http_atkomst() -> str | None
    mcp_http_app(mcp, host) -> Starlette
    BearerAuth(app, api_nyckel, sokvagsprefix="")
"""

from __future__ import annotations

import hmac
import logging
import os
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from mcp.server.mcpserver import MCPServer
    from starlette.applications import Starlette

logger = logging.getLogger(__name__)

PA = ("på", "pa", "ja", "1", "true", "on")


def starta(
    mcp: "MCPServer",
    standardport: int,
    initiera: Callable[[], None] | None = None,
    forvarm_http: Callable[[], None] | None = None,
) -> None:
    """Kör valfri initiering och startar den transport MCP_TRANSPORT anger.

    `initiera` körs i båda lägena och fångas i try/except. Servern ska gå
    upp i MCP-klienten även när databasen är nere; verktygsanropen felar
    då med ett begripligt meddelande, vilket är ett tydligare besked än en
    server som saknas i listan.

    `forvarm_http` körs bara i http-läget, före första anropet. Den är till
    för tunga resurser som embeddingmodeller: i stdio-läget laddas de hellre
    lat, så att klienten inte väntar på dem vid start.
    """
    if initiera is not None:
        try:
            initiera()
        except Exception as fel:
            logger.warning("Initiering misslyckades: %s. Fortsätter ändå.", fel)

    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()

    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport == "http":
        api_nyckel = http_atkomst()
        if forvarm_http is not None:
            forvarm_http()
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", str(standardport)))
        _starta_http(mcp, host=host, port=port, api_nyckel=api_nyckel)
        return

    logger.error(
        "Okänt värde för MCP_TRANSPORT: %r. Tillåtna värden: stdio, http.",
        transport,
    )
    sys.exit(2)


def http_atkomst() -> str | None:
    """Nyckeln som http-läget kräver, eller None i öppet läsläge.

    Avbryter med exitkod 2 när varken nyckel eller öppet läge är angivet.
    Är båda angivna gäller nyckeln: ett uttryckligt krav väger tyngre än
    ett uttryckligt undantag.
    """
    api_nyckel = os.getenv("MCP_API_KEY", "").strip()
    if api_nyckel:
        return api_nyckel
    if os.getenv("MCP_OPPEN_LASNING", "").strip().lower() in PA:
        logger.info("Öppet läsläge: http-läget kräver ingen nyckel.")
        return None
    logger.error(
        "MCP_API_KEY saknas och MCP_OPPEN_LASNING är inte satt. Uppstart i "
        "http-läge avbryts. Sätt en nyckel eller öppet läge i .env, eller "
        "använd MCP_TRANSPORT=stdio."
    )
    sys.exit(2)


def mcp_http_app(mcp: "MCPServer", host: str) -> "Starlette":
    """MCP-servern som Streamable HTTP-app med värdnamnen bakom proxyn tillåtna."""
    from mcp.server.transport_security import TransportSecuritySettings

    vardar = [v.strip() for v in os.getenv("MCP_TILLATNA_VARDAR", "").split(",") if v.strip()]
    sakerhet = None
    if vardar:
        sakerhet = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *vardar],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
                             *(f"https://{v}" for v in vardar)],
        )
    return mcp.streamable_http_app(host=host, transport_security=sakerhet)


class BearerAuth:
    """Kräver `Authorization: Bearer <nyckel>` på anrop under sokvagsprefix.

    Ren ASGI-middleware i stället för BaseHTTPMiddleware, så att strömmande
    MCP-svar inte buffras. Med ett prefix skyddas bara den delen av en app,
    till exempel MCP-servern under /mcp när den delar process med ett API.
    """

    def __init__(self, app, api_nyckel: str, sokvagsprefix: str = "") -> None:
        self.app = app
        self.nyckel = api_nyckel.encode()
        self.prefix = sokvagsprefix

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.prefix):
            await self.app(scope, receive, send)
            return
        from starlette.responses import JSONResponse

        huvuden = dict(scope.get("headers") or [])
        auth = huvuden.get(b"authorization", b"").decode("latin-1")
        if not auth.lower().startswith("bearer "):
            svar = JSONResponse({"fel": "Authorization-header saknas."}, status_code=401)
        # Jämförelse i konstant tid, så att nyckeln inte kan gissas tecken
        # för tecken utifrån svarstiden
        elif not hmac.compare_digest(auth.split(" ", 1)[1].strip().encode(), self.nyckel):
            svar = JSONResponse({"fel": "Ogiltig API-nyckel."}, status_code=403)
        else:
            await self.app(scope, receive, send)
            return
        await svar(scope, receive, send)


def _starta_http(mcp: "MCPServer", host: str, port: int, api_nyckel: str | None) -> None:
    """Startar Streamable HTTP via uvicorn, med Bearer-autentisering om nyckel finns.

    uvicorn och starlette importeras här, så att stdio-läget fungerar även
    där de inte är installerade.
    """
    import uvicorn

    app = mcp_http_app(mcp, host)
    if api_nyckel is not None:
        app = BearerAuth(app, api_nyckel)
    logger.info("MCP-servern lyssnar på http://%s:%s/mcp", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
