"""
Söktjänsten i drift: REST-API:et och MCP-servern i samma process.

Embeddingmodellerna laddas en gång och delas av båda. API:et svarar på
roten och MCP-servern på /mcp; reverse proxyn skickar api.fornmed.se till
roten och mcp.fornmed.se till /mcp.

MCP-delen följer samma åtkomstregler som när den körs ensam
(mcp_transport.py): antingen MCP_API_KEY, som då bara gäller /mcp, eller
uttryckligt öppet läsläge med MCP_OPPEN_LASNING=på. API:et är alltid öppet.

Miljövariabler (utöver databasens och embeddingmodellernas):
    FORNMED_HOST              adress att lyssna på   (standard: 127.0.0.1)
    FORNMED_PORT              port                   (standard: 8424)
    FORNMED_INITIERA_SCHEMA   på | av                (standard: på)

På servern ansluter tjänsten med en skrivskyddad roll och databasen kommer
färdig från utvecklingsdatorn; där sätts FORNMED_INITIERA_SCHEMA=av, så att
tjänsten inte försöker skapa tabeller vid start.

    python tjanst.py
"""

import contextlib
import logging
import os

# db läser .env vid import och måste därför importeras först
import db
import embeddings
import mcp_server
import uvicorn
from api import app
from mcp_transport import BearerAuth, http_atkomst, mcp_http_app

log = logging.getLogger("tjanst")


def skapa_app():
    """API-appen med MCP-servern monterad under /mcp."""
    api_nyckel = http_atkomst()
    host = os.getenv("FORNMED_HOST", "127.0.0.1")
    mcp_app = mcp_http_app(mcp_server.mcp, host)

    @contextlib.asynccontextmanager
    async def livscykel(_app):
        if os.getenv("FORNMED_INITIERA_SCHEMA", "på").strip().lower() not in ("av", "nej", "0", "false"):
            try:
                db.initiera_schema()
            except Exception as fel:
                log.warning("Databasinitiering misslyckades: %s. Fortsätter ändå.", fel)
        # Modellerna laddas före första anropet, så att den första sökningen
        # inte väntar på dem
        for modell in embeddings.MODELLER.values():
            embeddings._hamta_modell(modell)
        async with mcp_server.mcp.session_manager.run():
            yield

    app.router.lifespan_context = livscykel
    # MCP-appens egen rutt (/mcp) läggs direkt i API:ets router. Som Mount
    # skulle /mcp omdirigeras till /mcp/, vilket MCP-klienter inte följer.
    app.router.routes.extend(mcp_app.routes)
    if api_nyckel is not None:
        return BearerAuth(app, api_nyckel, sokvagsprefix="/mcp")
    return app


def main() -> None:
    host = os.getenv("FORNMED_HOST", "127.0.0.1")
    port = int(os.getenv("FORNMED_PORT", "8424"))
    log.info("Söktjänsten lyssnar på http://%s:%s (API på /, MCP på /mcp)", host, port)
    uvicorn.run(skapa_app(), host=host, port=port, log_level="info",
                proxy_headers=True, forwarded_allow_ips="127.0.0.1")


if __name__ == "__main__":
    main()
