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
import threading
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
        return date_time.strftime("%m/%d/%Y %H:%M")

    def write_migration(self, list_subs, list_terms, list_tokens, list_no_cumple_condicion, brand, writer_no_cumple_condicion, writer, flag):
        list_suspended = []
        for row in list_subs:
            token = ''

            if row.get('subscriptionId') in list_no_cumple_condicion:
                print('validando')
                continue

            data_subscription = SalesClient().get_subscription(
                site=brand,
                subscription_id=row.get('subscriptionId')
            )
            if data_subscription:
                if row.get(
                        'initialTransaction') == 'True':
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

                    period_from = timestamp_to_datetime(final_payment['periodFrom'])
                    next_event_date_utc = timestamp_to_datetime(data_subscription.get('nextEventDateUTC'))
                    if data_subscription.get('status') == Subscription.ARC_STATE_SUSPENDED:
                        period_to = timestamp_to_datetime(final_payment['periodTo']) + timedelta(days=29)
                        next_event_date_utc_suspendend = \
                            timestamp_to_datetime(data_subscription.get('nextEventDateUTC')) + timedelta(days=29)
                    else:
                        period_to = timestamp_to_datetime(final_payment['periodTo'])
                        next_event_date_utc_suspendend = ''
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
                            data_subscription.get('priceCode'),
                            data_subscription.get('sku'),
                            data_subscription.get('status'),
                            self.format_date(timestamp_to_datetime(final_payment['periodTo'])),
                            self.format_date(next_event_date_utc),
                            self.format_date(next_event_date_utc_suspendend) if next_event_date_utc_suspendend else ''
                        ]
                    )
                else:
                    if flag == 1:
                        writer_no_cumple_condicion.writerow(
                            [
                                'subscriptionId',
                                'status',
                                'initialTransaction'
                            ]
                        )
                        flag = flag + 1

                    writer_no_cumple_condicion.writerow(
                        [
                            row.get('subscriptionId'),
                            data_subscription.get('status'),
                            row.get('initialTransaction')
                        ]
                    )
            else:
                print('error_' + str(row.get('subscriptionId')))

    def handle(self, *args, **options):
        """
            - Genera el csv AID_psc_subs.csv para la migracion de terminos de pago
            - python3 manage.py migration_subscriptions --site gestion --rama sandbox
        """
        path = '/home/milei/Documentos/subscription_migration/'
        list_tokens = []
        list_terms = []
        list_subscriptions = []
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
        try:
            with open('{path}{rama}/sandbox-tokens.csv'.format(path=path, rama=rama)) as csvfileTokens:
                reader = csv.DictReader(csvfileTokens)
                for row in reader:
                    list_tokens.append({
                        'subscription_id': row.get('SUBSCRIPTION_ID', ''),
                        'payu_token': row.get('PAYU_TOKEN', ''),
                        'last_updated_utc': row.get('LAST_UPDATED_UTC', '')
                    })
            csvfileTokens.close()
        except:
            list_tokens = []

        ############################# FIN de extraccion de tokens ##################################
        ############################################################################################

        if options.get('site'):
            brand = options.get('site')
            #********************************************************************************************************
            #***************************** Obtiene la lista de terminos y PriceCode *********************************
            try:
                with open(path + rama + '/list_terms_gestion.csv') as csvfileTerms:
                    reader = csv.DictReader(csvfileTerms)
                    for row in reader:
                        list_terms.append({
                            'arc_price_code': row.get('arc_price_code', ''),
                            'term_id': row.get('term_id', '')
                        })
                csvfileTerms.close()
            except:
                list_terms = []
            # ***************************** Fin de lista de Terminos y PriceCode *************************************
            # ********************************************************************************************************
            # ********************************************************************************************************
            # ***************************** Obtiene la lista de no cumple condicion *********************************
            list_no_cumple_condicion = []
            try:
                with open(path + rama + '/no_cumple_condicion.csv') as csvfileNoCondition:
                    reader = csv.DictReader(csvfileNoCondition)
                    for row in reader:
                        list_no_cumple_condicion.append(row.get('subscriptionId', ''))
                csvfileNoCondition.close()
            except Exception as e:
                print(e)
                pass
            # ***************************** Fin de no cumple condicion************************************************
            # ********************************************************************************************************
            print(list_no_cumple_condicion)
            name_file_migration_subscriptions = '{path}{rama}/{brand}_subs_payu.csv'.format(
                brand=settings.PIANO_APPLICATION_ID[brand],
                path=path,
                rama=options['rama']
            )
            with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
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
                        'suscription_id',
                        'price_code',
                        'sku',
                        'status',
                        'next_billing_date_original',
                        'next_event_utc',
                        'next_event_utc_suspended'
                    ]
                )
                tiempo_ini = datetime.now()
                with open(path + rama + '/no_cumple_condicion.csv', 'a', encoding="utf-8") as csvFile2:
                    writer_no_cumple_condicion = csv.writer(csvFile2)
                    #path + rama + '/backup_' + rama + '.csv'
                    with open(path + rama + '/backup_' + rama + '.csv') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            list_subscriptions.append(
                                {
                                    'subscriptionId': row.get('subscriptionId'),
                                    'initialTransaction': row.get('initialTransaction'),
                                    'clientId': row.get('clientId')
                                }
                            )

                        n = 2000
                        name_hilo = 0
                        flag = 1
                        list_of_list = [list_subscriptions[i:i + n] for i in range(0, len(list_subscriptions), n)]
                        for list_subs in list_of_list:
                            name_hilo = name_hilo + 1
                            vars()['thread_' + str(name_hilo)] = threading.Thread(name="hilo_" + str(name_hilo), target=self.write_migration, args=(
                                list_subs, list_terms, list_tokens, list_no_cumple_condicion, brand,
                                writer_no_cumple_condicion, writer, flag,))
                            #time.sleep(2)
                            vars()['thread_' + str(name_hilo)].start()
                            vars()['thread_' + str(name_hilo)].join()
                            # self.write_migration(list_subs, list_terms, list_tokens, list_no_cumple_condicion, brand, writer_no_cumple_condicion, writer)
                        tiempo_fin = datetime.now()
                        print("tiempo transcurrido " + str(tiempo_fin - tiempo_ini))
                csvFile2.close()
            csvFilewrite.close()
            print('Termino la ejecucion del comando')

