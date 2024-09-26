# -*- coding: utf-8 -*-
import pytz
from django.core.management.base import BaseCommand
from apps.clubelcomercio.clients import ClubClient
from apps.piano.models import Subscription
from apps.clubelcomercio.models import ClubRegister
from apps.piano.utils.utils_functions import get_start_subscription
from apps.piano.utils.utils_functions import get_data_to_club


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--first_sale', nargs='?', type=str)
        parser.add_argument('--test_mode', nargs='?', type=str)
        parser.add_argument('--filter_elements', nargs='?', type=str)

    def handle(self, *args, **options):
        """
            - Servicio que envia los pendientes de envio a club
            - forma de envio python3 manage.py send_subscriptions_club
        """
        subscription_list = Subscription.objects.exclude(sent_club=True)
        for subscription in subscription_list:
            if subscription.start_date >= get_start_subscription(subscription.app_id):
                print(subscription.subscription_id)
                data = get_data_to_club(subscription)
                if data:
                    valida = ClubRegister.objects.filter(
                        subscription_str=subscription.subscription_id,
                        status_response=200
                    ).exists()
                    if data and not valida:
                        club_client = ClubClient()
                        club_client.register_club(body=data, club=ClubRegister())
                else:
                    print('Club Register no ejecutado')

        print('Termino la ejecucion del comando')
