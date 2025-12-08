import sys
from datetime import datetime
from typing import Callable

import structlog
from django.conf import settings
from django.db import connection
from django.utils import timezone

from fullctl.django.context import current_request

if "django_peeringdb" in settings.INSTALLED_APPS:
    import django_peeringdb.models.concrete as pdb_models
else:
    pdb_models = None

__all__ = [
    "error_context",
    "host_url",
    "load_branding_info",
    "verified_asns",
    "DEFAULT_FULLCTL_BRANDING",
    "get_db_connection_stats",
    "log_db_connection_stats",
]

log = structlog.get_logger(__name__)

DEFAULT_FULLCTL_BRANDING = {
    "name": "FullCtl",
    "html_footer": f"Copyright © 2014 - {datetime.now().year} FullCtl, LLC",
    "css": {"primary_color": "#D1FF27"},
    "dark_logo_url": None,
    "light_logo_url": None,
    "custom_org": False,
    "show_logo": True,
}


def error_context(status: int, exception: Exception, request) -> dict:
    if exception:
        exc_type = exception.__class__
    else:
        exc_type, exception, _ = sys.exc_info()
    request.error_response = exception

    return {
        "status": status,
        "type_description": f"{exc_type}",
        "description": f"{exception}",
        "path": request.path,
        "ip_address": request.META.get("HTTP_X_FORWARDED_FOR"),
        "referer": request.META.get("HTTP_REFERER"),
        "timestamp": timezone.now(),
    }


def load_branding_info(
    request, branding_org: str, fn_fetch: Callable, raise_errors: bool = False
) -> dict | None:

    if not branding_org:
        return None

    try:
        org_branding = fn_fetch(branding_org, request)

        if org_branding:
            return {
                "name": org_branding.org_name,
                "html_footer": org_branding.html_footer,
                "css": org_branding.css,
                "dark_logo_url": org_branding.dark_logo_url,
                "light_logo_url": org_branding.light_logo_url,
                "favicon_url": org_branding.favicon_url,
                "custom_org": True,
            }
    except Exception as e:
        # any exception here should be log, but not cause a
        # cascading error
        log.exception("Error getting branding", e=e)
        if raise_errors:
            raise e


def host_url():
    """
    Will see if a current request context exist and if it
    does return host url as it exists on the requests HTTP_HOST attribute.

    Otherwise settings.HOST_URL is returned
    """

    with current_request() as request:
        if request:
            return request.META.get("HTTP_ORIGIN", settings.HOST_URL)
        return settings.HOST_URL


def verified_asns(perms):

    verified_asns = []
    for verified_asn in perms.pset.expand("verified.asn.?", explicit=True, exact=True):
        asn = verified_asn.keys[-1]

        pdb_net = None
        if pdb_models:

            # if peeringdb is installed, we can look up the network locally
            # otherwise we will just return the asn

            try:
                pdb_net = pdb_models.Network.objects.get(asn=asn)
            except (ValueError, pdb_models.Network.DoesNotExist):
                pass

        verified_asns.append({"asn": asn, "pdb_net": pdb_net})

    return verified_asns


def get_db_connection_stats():
    """
    Get PostgreSQL connection statistics for the current database.
    
    Returns a dictionary with:
    - total_connections: Total number of connections to the database
    - active_connections: Number of active connections (state = 'active')
    - idle_connections: Number of idle connections
    - per_application: Dictionary of connection counts per application
    """
    try:
        db_name = connection.settings_dict['NAME']
        stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "per_application": {}
        }
        
        with connection.cursor() as cursor:
            # Get total connections
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s", 
                          [db_name])
            stats["total_connections"] = cursor.fetchone()[0]
            
            # Get active connections
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND state = 'active'", 
                          [db_name])
            stats["active_connections"] = cursor.fetchone()[0]
            
            # Get idle connections
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s AND state = 'idle'", 
                          [db_name])
            stats["idle_connections"] = cursor.fetchone()[0]
            
            # Get connections per application
            cursor.execute("""
                SELECT application_name, count(*) 
                FROM pg_stat_activity 
                WHERE datname = %s 
                GROUP BY application_name
            """, [db_name])
            
            for app_name, count in cursor.fetchall():
                stats["per_application"][app_name or "unknown"] = count
            
        return stats
    except Exception as exc:
        log.warning("Failed to get database connection statistics", exc=exc)
        return {"error": str(exc)}


def log_db_connection_stats(context=None):
    """
    Log database connection statistics.
    
    Args:
        context: Optional context information to include in the log message
    """
    db_stats = get_db_connection_stats()
    log_data = {
        "total": db_stats.get("total_connections"),
        "active": db_stats.get("active_connections"),
        "idle": db_stats.get("idle_connections"),
        "per_app": db_stats.get("per_application")
    }
    
    if context:
        log_data.update(context)
    
    log.debug("Database connections", **log_data)
