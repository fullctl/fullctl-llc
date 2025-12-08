try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
    BRIDGE_OBJECTS_CHUNK_SIZE = settings.BRIDGE_OBJECTS_CHUNK_SIZE
except Exception:
    DEFAULT_SERVICE_KEY = ""
    BRIDGE_OBJECTS_CHUNK_SIZE = 50

    class settings:
        AUDITCTL_URL = ""


import structlog

from fullctl.service_bridge.client import Bridge, DataObject, url_join
from fullctl.utils import chunk_list

CACHE = {}

logger = structlog.get_logger(__name__)


class AuditctlEntity(DataObject):
    description = "AuditCtl Object"
    source = "auditctl"


class Auditctl(Bridge):
    """
    Service bridge to auditctl for data
    retrieval
    """

    class Meta:
        service = "auditctl"
        ref_tag = "base"
        data_object_cls = AuditctlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.AUDITCTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class Event(Auditctl):
    class Meta(Auditctl.Meta):
        ref_tag = "event"

    def log_action(
        self,
        org_slug: str,
        service: str,
        ref_tag: str,
        action: str,
        id: int | str | None = None,
        request_url: str | None = None,
        payload: dict | None = None,
        status_code: int = 200,
        append_path: list[str] | None = None,
        error_message: str = "",
        api_key: str = "",
        username: str = "",
    ):
        """
        Logs an action to the auditctl service

        Arguments:
            username (`str`): username of the user performing the
            org_slug (`str`): org slug
            service (`str`): service name (e.g. "ixctl")
            ref_tag (`str`): reference tag (e.g. "member")
            action (`str`): action being performed (e.g. "create")
            payload (`dict`): request payload
            status_code (`int`): status code of the request
            append_path (`list`): additional path components
            error_message (`str`): error message
        """

        object_id = f"v0.1/{org_slug}/action/{service}/{ref_tag}/{action}/"

        if append_path:
            object_id = url_join(object_id, *append_path)

        components = [
            {
                "kind": "request",
                "id": id,
                "action": action,
                "payload": payload,
                "service": service,
                "ref_tag": ref_tag,
                "username": username,
                "api_key": api_key[:4] + "..." + api_key[-4:] if api_key else None,
                "url": request_url,
            },
            {
                "kind": "response",
                "status_code": status_code,
            },
        ]

        logger.debug(f"Logging action: {object_id}", components=components)

        if status_code < 400:

            # log the event as successful

            Event().create(
                {
                    "org": org_slug,
                    "object_id": object_id,
                    "status": "ok",
                    "source": service,
                    "data": {
                        "components": components,
                    },
                }
            )
        elif status_code >= 500:

            # log the event as failed
            # Current assumption is that we dont want log 4xx errors

            Event().create(
                {
                    "org": org_slug,
                    "object_id": object_id,
                    "status": "error",
                    "source": service,
                    "error": {
                        "message": f"Request failed with status code {status_code}\n{error_message}",
                        "components": components,
                    },
                }
            )

    def send_email(
        self,
        org_slug: str,
        source_service_tag: str,
        category: str,
        subject: str,
        message: str,
        recipients: list[str],
    ) -> None:
        """
        Sends an email via auditctl
        """
        event_id = f"v0.1/{org_slug}/notification/{category}"
        self.create(
            {
                "org": org_slug,
                "object_id": event_id,
                "status": "ok",
                "source": source_service_tag,
                "data": {
                    "components": [
                        {
                            "id": "",
                            "kind": "email",
                            "subject": subject,
                            "message": message,
                            "recipients": recipients,
                        }
                    ]
                },
            },
        )

    def send_error_email(
        self,
        org_slug: str,
        source_service_tag: str,
        category: str,
        subject: str,
        message: str,
        recipients: list[str],
    ) -> None:
        """
        Wrapper for send_email that sends an email with a category of 'error'
        """

        self.send_email(
            source_service_tag=source_service_tag,
            org_slug=org_slug,
            category=f"error/{source_service_tag}/{category}",
            subject=subject,
            message=message,
            recipients=recipients,
        )

    def get_last_updated_config_liveness_event(self, org_slug: str):
        """
        Get the config liveness event for an org

        Arguments:
            org_slug (`str`) -- org slug
        """
        return self.get(f"data/event/v0.1/{org_slug}/config/liveness/")

    def get_events_by_ids(self, event_ids):
        if len(event_ids) <= BRIDGE_OBJECTS_CHUNK_SIZE:
            return list(self.objects(ids=event_ids))

        events = []
        for event_ids_chunk in chunk_list(
            data=event_ids, chunk_size=BRIDGE_OBJECTS_CHUNK_SIZE
        ):
            events.extend(list(self.objects(ids=event_ids_chunk)))
        return events
