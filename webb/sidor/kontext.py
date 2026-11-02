"""Uppgifter som alla mallar behöver: menyn, statistiken och tjänsternas adresser."""

from django.conf import settings
from wagtail.models import Site


def webbplats(request):
    site = Site.find_for_request(request)
    meny = []
    if site:
        meny = site.root_page.get_children().live().in_menu().specific()
    return {
        "meny": meny,
        "startsida": site.root_page if site else None,
        "statistik_url": settings.WEBB_STATISTIK_URL,
        "statistik_id": settings.WEBB_STATISTIK_ID,
        "api_url": settings.API_URL,
        "mcp_url": settings.MCP_URL,
    }
