# these are deprecated since they use django settings directly instead of going
# through the social_core.settings module

import warnings

warnings.warn(
    "These are deprecated in favor of fullctl.social.backends",
    DeprecationWarning,
)
