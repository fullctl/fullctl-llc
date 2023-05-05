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


class ServiceApplication(Aaactl):
    class Meta(Aaactl.Meta):
        ref_tag = "service_application"
        data_object_cls = ServiceApplicationObject


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

    def get_product_property(self, component, org, property_name):
        for org_product in self.objects(component=component, org=org):
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
