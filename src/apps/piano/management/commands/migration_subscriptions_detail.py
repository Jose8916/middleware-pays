# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception

from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment, \
    SubscriptionExclude
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient
from django.utils.encoding import smart_str
import csv
import time
from apps.piano.piano_clients import VXClient
from apps.arcsubs.utils import timestamp_to_datetime


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def format_date_str(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m-%d-%Y %H:%M")

    def handle(self, *args, **options):
        """
            - Genera el csv AID_psc_subs.csv para la migracion de terminos de pago
            - python3 manage.py migration_subscriptions_detail --site gestion --rama sandbox
        """
        path = '/home/milei/Documentos/subscription_migration/'
        list_tokens = []
        list_terms = []
        count = 0
        flag = 1
        rama = options['rama']

        ############################################################################################
        ############################# extrae los tokens del archivo ################################
        """
        with open('{path}{rama}/tokens.txt'.format(path=path, rama=options['rama']), "r") as tf:
            lines = tf.readlines()

        for row in lines:
            if count == 0:
                count = count + 1
                continue

            row = row.replace('"', '').split(",")
            list_tokens.append({
                'subscription_id': row[0],
                'payu_token': row[1],
                'last_updated_utc': row[2]
            })
        """
        with open('{path}{rama}/gestion-sandbox-tokens.csv'.format(path=path, rama=rama)) as csvfileTokens:
            reader = csv.DictReader(csvfileTokens)
            for row in reader:
                list_tokens.append({
                    'subscription_id': row.get('SUBSCRIPTION_ID', ''),
                    'payu_token': row.get('PAYU_TOKEN', ''),
                    'last_updated_utc': row.get('LAST_UPDATED_UTC', '')
                })
        csvfileTokens.close()

        ############################# FIN de extraccion de tokens ##################################
        ############################################################################################

        if options.get('site'):
            brand = options.get('site')
            #********************************************************************************************************
            #***************************** Obtiene la lista de terminos y PriceCode *********************************

            with open(path + rama + '/list_terms.csv') as csvfileTerms:
                reader = csv.DictReader(csvfileTerms)
                for row in reader:
                    list_terms.append({
                        'arc_price_code': row.get('arc_price_code', ''),
                        'term_id': row.get('term_id', '')
                    })
            csvfileTerms.close()
            # ***************************** Fin de lista de Terminos y PriceCode *************************************
            # ********************************************************************************************************

            name_file_migration_subscriptions = '{path}{rama}/{brand}_subs_payu_detail.csv'.format(
                brand=settings.PIANO_APPLICATION_ID[brand],
                path=path,
                rama=options['rama']
            )
            with open(name_file_migration_subscriptions, 'a') as csvFilewrite:
                writer = csv.writer(csvFilewrite)
                writer.writerow(
                    [
                        'user_id',
                        'term_id',
                        'customer_id',
                        'start_date',
                        'next_billing_date',
                        'prev_billing_date',
                        'payment_method_token',
                        'card_id',
                        'custom_billing_plan',
                        'auto_renew',
                        'provider_input_params',
                        'expiration',
                        'suscription',
                        'plan',
                        'price_code',
                        'sku'
                    ]
                )
                with open(path + rama + '/no_cumple_condicion_detail.csv', 'a') as csvFile2:
                    writer_ = csv.writer(csvFile2)

                    with open(path + rama + '/backup_' + rama + '.csv') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            time.sleep(1)
                            data_subscription = SalesClient().get_subscription(
                                site=brand,
                                subscription_id=row.get('subscriptionId')
                            )
                            if data_subscription:
                                if data_subscription.get('status') != Subscription.ARC_STATE_TERMINATED and row.get('initialTransaction') == 'True':
                                    # subcription_obj = Subscription.objects.get(arc_id=row.get('subscriptionId'))
                                    # subcription_obj.plan.term_id
                                    term_id = ''
                                    for term_obj in list_terms:
                                        if data_subscription.get('priceCode') == term_obj.get('arc_price_code', ''):
                                            term_id = term_obj.get('term_id', '')

                                    final_payment = data_subscription.get('paymentHistory')[-1]
                                    for event in data_subscription.get('events'):
                                        if event['eventType'] == "START_SUBSCRIPTION":
                                            date_start_subscription = timestamp_to_datetime(event['eventDateUTC'])
                                            break

                                    if data_subscription.get('status') == Subscription.ARC_STATE_SUSPENDED:
                                        period_to = timestamp_to_datetime(final_payment['periodTo']) + timedelta(
                                            days=29)
                                    else:
                                        period_to = timestamp_to_datetime(final_payment['periodTo'])
                                    period_from = timestamp_to_datetime(final_payment['periodFrom'])

                                    if data_subscription.get('status') == Subscription.ARC_STATE_CANCELED:
                                        auto_renew = 'false'
                                    else:
                                        auto_renew = 'true'

                                    for token_obj in list_tokens:
                                        if token_obj.get('subscription_id') == str(row.get('subscriptionId')):
                                            token = token_obj.get('payu_token')
                                            break
                                        else:
                                            token = ''

                                    writer.writerow(
                                        [
                                            row.get('clientId'),
                                            term_id,
                                            '',
                                            self.format_date(date_start_subscription),
                                            self.format_date(period_to),
                                            self.format_date(period_from),
                                            token,
                                            '',
                                            '',
                                            auto_renew,
                                            '"{""country_code"": ""PE""}"',
                                            '',
                                            row.get('subscriptionId'),
                                            'plan',
                                            data_subscription.get('priceCode'),
                                            data_subscription.get('sku')
                                        ]
                                    )
                                    print('ingresa')
                            else:
                                print('error')
                                print(row.get('subscriptionId'))
                                time.sleep(5)

                csvFile2.close()
            csvFilewrite.close()
            print('Termino la ejecucion del comando')

