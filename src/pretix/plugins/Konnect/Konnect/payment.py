import json
import logging
import urllib.parse
from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.core import signing
from django.http import HttpRequest
from django.forms import MultipleChoiceField, ChoiceField, Form
from django.template.loader import get_template
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as __, gettext_lazy as _
from i18nfield.strings import LazyI18nString
from django_countries import countries


from pretix.base.decimal import round_decimal
from pretix.base.models import Event, Order, OrderPayment, OrderRefund, Quota
from pretix.base.payment import BasePaymentProvider, PaymentException
from pretix.base.services.mail import SendMailException
from pretix.base.settings import SettingsSandbox
from pretix.multidomain.urlreverse import build_absolute_uri





logger = logging.getLogger('pretix.plugins.Konnect.Konnect')

SUPPORTED_CURRENCIES = ['AUD', 'BRL', 'CAD', 'CZK', 'DKK', 'EUR', 'HKD', 'HUF', 'INR', 'ILS', 'JPY', 'MYR', 'MXN',
                        'TWD', 'NZD', 'NOK', 'PHP', 'PLN', 'GBP', 'RUB', 'SGD', 'SEK', 'CHF', 'THB', 'USD', 'TND']

LOCAL_ONLY_CURRENCIES = ['TND']

class Konnect(BasePaymentProvider):
    identifier = 'konnect'
    verbose_name = _('Konnect')
    payment_form_fields = OrderedDict([
    ])

    def __init__(self, event: Event):
        super().__init__(event)
        self.settings = SettingsSandbox('payment', 'konnect', event)


    @property
    def test_mode_message(self):
        if self.settings.connect_client_id and not self.settings.secret:
            # in OAuth mode, sandbox mode needs to be set global
            is_sandbox = self.settings.connect_endpoint == 'sandbox'
        else:
            is_sandbox = self.settings.get('endpoint') == 'sandbox'
        if is_sandbox:
            return _('The Konnect sandbox is being used, you can test without actually sending money but you will need a '
                     'Konnect sandbox user to log in.')
        return None

    @property
    def settings_form_fields(self):
        fields = [
                ('client_id',
                 forms.CharField(
                     label=_('Wallet ID'),
                     max_length=80,
                     min_length=2,
                     help_text=_('<a target="_blank" rel="noopener" href="{docs_url}">{text}</a>').format(
                         text=_('Click here To Login or Signup on KONNECT for <font size="3" face="verdana"color="red">Live Mode </font>'),
                         docs_url='https://konnect.network/admin/login'
                     )
                 )),
                ('api_key',
                 forms.CharField(
                     label=_('API Key'),
                     max_length=80,
                     min_length=2,
                     help_text=_('<a target="_blank" rel="noopener" href="{docs_url}">{text}</a>').format(
                         text=_('How to get my API Key on KONNECT '),
                         docs_url='https://api.konnect.network/api/v2/konnect-gateway'
                     )
                     )),
                ('client_id_test',
                 forms.CharField(
                     label=_('Wallet ID (Test)'),
                     max_length=80,
                     min_length=2,
                     required=False,
                     help_text=_('<a target="_blank" rel="noopener" href="{docs_url}">{text}</a>').format(
                         text=_('Click here To Login or Signup on KONNECT for <font size="3" face="verdana"color="green">Test Mode</font>'),
                         docs_url='https://preprod.konnect.network/admin/login'
                     )
                 )),
                ('api_key_test',
                 forms.CharField(
                     label=_('API Key (Test)'),
                     max_length=80,
                     min_length=2,
                     required=False,
                     help_text=_('<a target="_blank" rel="noopener" href="{docs_url}">{text}</a>').format(
                         text=_('How to get my API Key on KONNECT '),
                         docs_url='https://api.konnect.network/api/v2/konnect-gateway'
                     )
                     )),
                
                
                ('Bank_card',
                 forms.BooleanField(
                     label=_('Credit Card'),
                     required=False,
                     initial= True,
                 )),
                ('Wallet',
                 forms.BooleanField(
                     label=_('Konnect Wallet'),
                     required=False,
                 )),
                ('E-DINAR',
                 forms.BooleanField(
                     label=_('E-DINAR'),
                     initial= True,
                     required=False,
                 )),
                 ('Flouci',
                 forms.BooleanField(
                     label=_('Flouci'),
                     required=False,
                 )), 
            ]
        d = OrderedDict(
            list(super().settings_form_fields.items()) + fields
        )

        d.move_to_end('_enabled', False)
        return d

    def _create_payment(self, request, payment):
        if payment.create():
             if payment.state not in ('created', 'approved', 'pending'):
                messages.error(request, _('We had trouble communicating with Konnect'))
                logger.error('Invalid payment state: ' + str(payment))
             return 
             request.session['payment_konnect_id'] = payment.id
             for link in payment.links:
                if link.method == "REDIRECT" and link.rel == "approval_url":
                    if request.session.get('iframe_session', False):
                        signer = signing.Signer(salt='safe-redirect')
                        return (
                            build_absolute_uri(request.event, 'plugins:Konnect:redirect') + '?url=' +
                            urllib.parse.quote(signer.sign(link.href))
                        )
                    else:
                        return str(link.href)
        else:
            messages.error(request, _('We had trouble communicating with Konnect'))
            logger.error('Error on creating payment: ' + str(payment.error))

    def payment_is_valid_session(self, request):
        if "payment_konnect_id" in request.session:
            result = request.session["payment_konnect_id"]
        else:
            result = False


    
    def payment_form_render(self, request) -> str:
        template = get_template('konnect/checkout_payment_form.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)

    def checkout_confirm_render(self, request) -> str:
        """
        Returns the HTML that should be displayed when the user selected this provider
        on the 'confirm order' page.
        """
        template = get_template('/Konnect/checkout_payment_confirm.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)




    def payment_prepare(self, request, payment_obj):
        self.init_api()

        try:
            if request.event.settings.payment_konnect_connect_user_id:
                try:
                    tokeninfo = Tokeninfo.create_with_refresh_token(request.event.settings.payment_konnect_connect_refresh_token)
                except BadRequest as ex:
                    ex = json.loads(ex.content)
                    messages.error(request, '{}: {} ({})'.format(
                        _('We had trouble communicating with PayPal'),
                        ex['error_description'],
                        ex['correlation_id'])
                    )
                    return

                # Even if the token has been refreshed, calling userinfo() can fail. In this case we just don't
                # get the userinfo again and use the payment_paypal_connect_user_id that we already have on file
                try:
                    userinfo = tokeninfo.userinfo()
                    request.event.settings.payment_konnect_connect_user_id = userinfo.email
                except UnauthorizedAccess:
                    pass

                payee = {
                    "email": request.event.settings.payment_konnect_connect_user_id,
                    # If PayPal ever offers a good way to get the MerchantID via the Identifity API,
                    # we should use it instead of the merchant's eMail-address
                    # "merchant_id": request.event.settings.payment_paypal_connect_user_id,
                }
            else:
                payee = {}

            request.session['payment_konnect_payment'] = payment_obj.pk
            return self._create_payment(request, payment)
        except paypalrestsdk.exceptions.ConnectionError as e:
            messages.error(request, _('We had trouble communicating with Konnect'))
            logger.exception('Error on creating payment: ' + str(e))