from typing import Callable

try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except Exception:
    # Improperly configured or django not installed
    # Improperly configured will be raised elsewhere in the app, so we can
    # ignore it here
    #
    # this allows us to use the service bridge in non-django environments
    DEFAULT_SERVICE_KEY = ""

    class settings:
        AAACTL_URL = ""


from fullctl.service_bridge.client import Bridge, DataObject, url_join

CACHE = {}


class AaactlEntity(DataObject):
    source = "aaactl"
    description = "Aaactl Object"


class Aaactl(Bridge):
    """
    Service bridge for aaactl data retrieval
    """

    class Meta:
        service = "aaactl"
        ref_tag = "base"
        data_object_cls = AaactlEntity

    def __init__(self, key=None, org=None, **kwargs):
        if not key:
            key = DEFAULT_SERVICE_KEY

        kwargs.setdefault("cache_duration", 10)
        kwargs.setdefault("cache", CACHE)

        super().__init__(settings.AAACTL_URL, key, org, **kwargs)
        self.url = url_join(self.url, "service-bridge/")


class ServiceApplicationObject(AaactlEntity):
    description = "Aaactl ServiceApplication"

    def for_org(self, org):
        if org:
            self.org_redirect = self.service_url.format(org=org)
            self.org_namespace = f"{self.grainy}.{org.permission_id}"
        else:
            self.org_redirect = self.api_url
            self.org_namespace = self.grainy
        return self

    def sanitize(self):
        # config may contain sensitive information, so we remove it
        delattr(self, "config")
        return self


class ServiceApplication(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "service_application"
        data_object_cls = ServiceApplicationObject

    def trial_available(self, org_slug, service_slug, object_id=None):
        params = {
            "org_slug": org_slug,
            "service_slug": service_slug,
            "object_id": object_id,
        }

        url = f"data/{self.ref_tag}/trial_available/"

        data = self.get(url, params=params)

        if data:
            return data[0]["can_trial"]
        return False


class FederatedServiceURL(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "federated_service_url"

    def federated_services(
        self, service_slugs: list[str], make_tag: Callable, source_ids: list[str]
    ) -> dict[str, dict[str, AaactlEntity]]:
        """
        Takes a list service bridge source ids - e.g., 'pdbctl:123' or 'ixctl:123'
        and returns a mapping of source id to the federated ixctl instance if it exists.

        Will return a dict of the form:

        {
            <service_slug>: {
                <source_id>: <FederatedServiceURL>
            },
            ...
        }
        """

        # convert from {source}:{id} (source) to ix.{source}.{id} (tag)
        tags = [make_tag(source_id) for source_id in source_ids]

        federated_service_urls = list(self.objects(tags=tags, slugs=service_slugs))

        result = {}

        for source_id in source_ids:
            tag = make_tag(source_id)
            for service_url in federated_service_urls:
                result.setdefault(service_url.service_slug, {})
                if tag in service_url.tags:
                    result[service_url.service_slug][source_id] = service_url
                    break

        return result


class User(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "user"
        data_object_cls = AaactlEntity


class OrganizationObject(AaactlEntity):
    description = "Aaactl Organization"


class Organization(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "organization"
        data_object_cls = OrganizationObject


class Product(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "product"


class OrganizationProduct(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "org_product"

    def get_product_property(
        self, component, org, property_name, component_object_id=None
    ):
        filters = dict(component=component, org=org)

        if component_object_id:
            filters["component_object_id"] = component_object_id

        for org_product in self.objects(**filters):
            if not org_product.product_data:
                continue

            if property_name in org_product.product_data.__dict__:
                return org_product.product_data.__dict__[property_name]

        return None


class Impersonation(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "impersonation"

    def stop(self, superuser_id):
        """
        Stops the impersonation of a user for the
        given superuser
        """

        impersonation = self.first(superuser=superuser_id)

        print("impersonation", impersonation, superuser_id)

        if not impersonation:
            return

        self.destroy(impersonation)


class ContactMessage(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "contact_message"


class OauthAccessToken(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "oauth_access_token"


class OrganizationBrandingObject(AaactlEntity):
    description = "Aaactl OrganizationBranding"


class OrganizationBranding(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "org_branding"
        data_object_cls = OrganizationBrandingObject


class PointOfContactObject(AaactlEntity):
    description = "Aaactl Point of Contact"


class PointOfContact(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "poc"
        data_object_cls = PointOfContactObject

    def save_poc(
        self,
        org_id: int,
        org_slug: str,
        delivery_type: str,
        service: str,
        poc_type: str,
        recipients: list[str] | None,
        entity: int | None = None,
    ):
        status = "ok"
        poc_objects = self.get(
            "data/poc/",
            params={
                "org": org_slug,
                "delivery_type": delivery_type,
                "status": status,
                "type": poc_type,
            },
        )
        if not poc_objects:
            if not recipients:
                return

            data = {
                "org": org_id,
                "delivery_type": delivery_type,
                "config": [
                    {"service": service, "recipients": recipients, "entity": entity}
                ],
                "type": poc_type,
                "status": status,
            }
            return self.create_poc(data)

        poc = poc_objects[0]
        for index, config in enumerate(poc.get("config", [])):
            if config.get("service") == service and config.get("entity") == entity:
                if not recipients:
                    del poc["config"][index]
                    break
                config["recipients"] = recipients
                break
        else:
            if recipients:
                poc["config"] = poc.get("config", []) + [
                    {"service": service, "recipients": recipients, "entity": entity}
                ]
            else:
                return

        return self.update_poc(poc.get("id"), poc)

    def create_poc(self, data: dict):
        """
        Create Point Of Contact

        Arguments:
            data (`dict`) -- The point of contact details
        """
        return self.post("data/poc/", json=data)

    def update_poc(self, poc_id: int, data: dict):
        """
        Update Point Of Contact

        Arguments:
            data (`dict`) -- The point of contact details
        """
        return self.put(f"data/poc/{poc_id}", json=data)

    def get_recipients(
        self,
        org,
        service: str,
        entity: int | None = None,
        delivery_type: str = "email",
        poc_type: str = "notifications",
    ) -> list[str]:
        """
        Get the service alert recipients for an org regardless
        of the delivery type
        """

        params = {
            "org": org.slug,
            "status": "ok",
        }

        if poc_type:
            params["type"] = poc_type

        if delivery_type:
            params["delivery_type"] = delivery_type

        if entity:
            params["entity"] = entity

        poc_objects = self.get("data/poc/", params=params)
        if not poc_objects:
            return None

        for config in poc_objects[0].get("config", []):
            if config.get("service") != service:
                continue

            if entity and config.get("entity") != entity:
                continue

            return config.get("recipients", [])
        return []

    def get_email_alert_recipients(
        self, org, service: str, entity: int | None = None
    ) -> list[str]:
        """
        Get the service email alert recipients for an org
        """
        return self.get_recipients(
            org,
            service,
            entity=entity,
            delivery_type="email",
            poc_type="notifications",
        )
