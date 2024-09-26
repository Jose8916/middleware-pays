from django.conf import settings
from django.core.management.base import BaseCommand
from sentry_sdk import capture_exception

from ...utils_siebel import SiebelClientSender
from apps.paywall.models import PaymentProfile, Payment
from apps.siebel.models import SiebelConfiguration, PendingSendSiebel
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Comando que envía los perfiles de compra a Siebel'

    def add_arguments(self, parser):
        parser.add_argument('--id_user_tabla', nargs='?', type=str)

    def handle(self, *args, **options):
        pendings = PendingSendSiebel.objects.all()

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
                    siebel_entecode=None,
                    siebel_hits__lte=int(config_siebel.customer_attempts),
                    created__range=[last_month, ahora]
                )
            elif settings.ENVIRONMENT == 'production':
                payment_profiles = PaymentProfile.objects.filter(
                    siebel_entecode=None,
                    siebel_hits__lte=int(config_siebel.customer_attempts)
                )

        for payment_profile in payment_profiles:
            print(payment_profile.id)
            siebel_client = SiebelClientSender(payment_profile)

            try:
                siebel_client.run()
            except Exception:
                capture_exception()
