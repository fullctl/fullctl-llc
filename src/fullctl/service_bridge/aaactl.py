from typing import Callable
try:
    from django.conf import settings

    DEFAULT_SERVICE_KEY = settings.SERVICE_KEY
except (ImportError, AttributeError):
    DEFAULT_SERVICE_KEY = ""

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

    def federated_services(self, service_slugs:list[str], make_tag:Callable, source_ids:list[str]) -> dict[str, dict[str, AaactlEntity]]:
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
        
        federated_service_urls = list(self.objects(
            tags=tags,
            slugs=service_slugs
        ))

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
