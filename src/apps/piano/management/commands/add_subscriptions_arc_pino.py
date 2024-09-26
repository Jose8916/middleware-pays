# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.piano.models import SubscriptionMatchArcPiano, Subscription

from datetime import datetime, timedelta
from django.db.models import Count
from django.utils.encoding import smart_str
import csv
import time
from apps.piano.piano_clients import VXClient
from apps.arcsubs.utils import timestamp_to_datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    #  python3 manage.py add_subscriptions_arc_pino --update 1

    def add_arguments(self, parser):
        parser.add_argument('--load', nargs='?', type=str)
        parser.add_argument('--update', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('load'):
            with open('/tmp/subscription_match.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not SubscriptionMatchArcPiano.objects.filter(
                        subscription_id_arc=row.get('arc_subscription_id'),
                        subscription_id_piano=row.get('piano_subscription_id')
                    ).exists():
                        subscription_obj = SubscriptionMatchArcPiano(
                            subscription_id_arc=row.get('arc_subscription_id'),
                            subscription_id_piano=row.get('piano_subscription_id'),
                            brand=row.get('brand')
                        )
                        print('guardando ' + str(row.get('arc_subscription_id')))
                        subscription_obj.save()
        if options.get('update'):
            subscriptions = SubscriptionMatchArcPiano.objects.filter(brand__isnull=True)
            for sub in subscriptions:
                try:
                    piano_sub = Subscription.objects.get(subscription_id=sub.subscription_id_piano)
                except:
                    piano_sub = ''
                if piano_sub:
                    if piano_sub.app_id == settings.PIANO_APPLICATION_ID['gestion']:
                        brand = 'gestion'
                    elif piano_sub.app_id == settings.PIANO_APPLICATION_ID['elcomercio']:
                        brand = 'elcomercio'
                    else:
                        brand = ''
                    if brand:
                        sub.brand = brand
                        sub.save()

        print('Termino la ejecucion del comando')
