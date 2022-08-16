# Register your receivers here
import json
from collections import OrderedDict

from django import forms
from django.dispatch import receiver
from django.http import HttpRequest, HttpResponse
from django.template.loader import get_template
from django.urls import resolve
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from pretix import settings
from pretix.base.forms import SecretKeySettingsField
from pretix.base.middleware import _merge_csp, _parse_csp, _render_csp
from pretix.base.settings import settings_hierarkey
from pretix.base.signals import (
    logentry_display, register_global_settings, register_payment_providers,
)
from pretix.presale.signals import html_head, process_response


@receiver(register_payment_providers, dispatch_uid="payment_konnect")
def register_payment_provider(sender, **kwargs):
    from .payment import Konnect
    return Konnect


@receiver(signal=logentry_display, dispatch_uid="konnect_logentry_display")
def pretixcontrol_logentry_display(sender, logentry, **kwargs):
    from pretix.plugins.paypal2.signals import pretixcontrol_logentry_display

    return pretixcontrol_logentry_display(sender, logentry, **kwargs)