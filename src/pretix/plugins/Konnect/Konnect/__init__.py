from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")

__version__ = "1.0.0"


class KonnectApp(PluginConfig):
    name = "pretix.plugins.Konnect.Konnect"
    verbose_name = "Konnect"

    class PretixPluginMeta:
        name = gettext_lazy("Konnect")
        author = "Konnect"
        description = gettext_lazy("it's a beta")
        visible = True
        version = __version__
        category = "PAYMENT"
        picture = 'Konnect\konnect_logo.svg'
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = "pretix.plugins.Konnect.Konnect.KonnectApp"
