from django.conf import settings
from django.core.management.base import BaseCommand
from sentry_sdk import capture_exception

from ...utils_siebel import SiebelClientSender
from apps.paywall.shortcuts import render_send_email
from apps.paywall.models import PaymentProfile, Payment, Partner
from apps.piano.constants import LIST_EMAIL_SENDER
from apps.siebel.models import SiebelConfiguration
from datetime import datetime, timedelta
from django.utils import formats, timezone
import requests


class Command(BaseCommand):
    help = 'Comando que envía los perfiles de compra a Siebel'
    """
    python3 manage.py siebel_createclient --id_user_tabla 26661
    """

    def add_arguments(self, parser):
        parser.add_argument('--id_user_tabla', nargs='?', type=str)
        parser.add_argument('--with_ente', nargs='?', type=str)

    def handle(self, *args, **options):
        list_ente_error = []
        current_month = datetime.now().month
        ahora = datetime.utcnow()
        config_siebel = SiebelConfiguration.objects.get(state=True)
        last_month = ahora - timedelta(days=int(config_siebel.days_ago))

        if options.get('id_user_tabla'):
            payment_profiles = PaymentProfile.objects.filter(
                id=options.get('id_user_tabla'),
                siebel_entecode=None,
                siebel_hits__lte=int(config_siebel.customer_attempts)
            )
        else:
            if settings.ENVIRONMENT == 'test':
                payment_profiles = PaymentProfile.objects.filter(
                    siebel_entedireccion=None,
                    siebel_hits__lte=int(config_siebel.customer_attempts),
                    created__range=[last_month, ahora]
                )
            elif settings.ENVIRONMENT == 'production':
                payment_profiles = PaymentProfile.objects.filter(
                    siebel_entedireccion=None,
                    siebel_hits__lte=int(config_siebel.customer_attempts)
                )
        print('total: ' + str(payment_profiles.count()))
        for payment_profile in payment_profiles:
            ente_error = None
            print(payment_profile.id)
            siebel_client = SiebelClientSender(payment_profile)

            try:
                ente_error = siebel_client.run()
            except Exception:
                capture_exception()

            tz = timezone.get_current_timezone()
            if ente_error and payment_profile.created >= datetime.strptime('12/12/2022', '%m/%d/%Y').astimezone(tz):
                list_ente_error.append(ente_error)

        if list_ente_error:
            try:
                partner = Partner.objects.get(partner_code=self.brand)
            except Exception:
                partner = None
            if partner:
                from_email = '{name_sender} <{direction_sender}>'.format(
                    name_sender=partner.partner_name,
                    direction_sender=partner.transactional_sender
                )
            else:
                from_email = None

            render_send_email(
                template_name='mailings/error.html',
                subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' No creo entecode',
                to_emails=LIST_EMAIL_SENDER,
                from_email=from_email,
                context={
                    'error': 'no creo entecode ' + str(list_ente_error),
                }
            )

