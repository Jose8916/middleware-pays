from django.core.management.base import BaseCommand

from apps.paywall.models import  SubscriptionState
from django.conf import settings


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        print(settings.PAYWALL_SIEBEL_IP)
        # SubscriptionState.objects.all().delete()




