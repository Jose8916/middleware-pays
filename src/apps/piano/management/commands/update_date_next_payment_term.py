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
    #  python3 manage.py update_date_next_payment --site gestion --rama production

    def add_arguments(self, parser):
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def format_date_str(self, date_time_str):
        date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        return date_time_obj.strftime("%m-%d-%Y %H:%M")

    def format_date(self, date_time):
        return date_time.strftime("%m/%d/%Y %H:%M")

    def update_next_billing_date(self, term_id, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = datetime.strptime(date_to_update, "%m/%d/%Y %H:%M")
        if date_time_obj.month == 5 and date_time_obj.year == 2022:
            if 11 <= date_time_obj.day <= 17:
                return date_to_update
            else:
                if term_id in \
                        [
                            'TMMBMPHLTJOU',
                            'TMUJV1J4URGK',
                            'TMKSL79R0303',
                            'TMZWR5XA4U4C',
                            'TMRP2L7BH02O',
                            'TM5FCZ7WXKEC',
                            'TMZ3DTMW5VIU',
                            'TMXRXOXCM4HD',
                            'TMLZQ7HIPMYV',
                            'TMVLHZHGBSF0',
                            'TM9879XA1D6W',
                            'TM2A7YAH6PUY',
                            'TMFZM0EFIB06',
                            'TMIPIRH8NWF5',
                            'TMV31V5O12AX',
                            'TMC80Y1RQEYB',
                            'TMXVURURISBW',
                            'TM1I0PUIVJOB',
                            'TMQEJFJ905DX',
                            'TMLZ9RUGY7PU',
                            'TMQQ17GSFLR1',
                            'TMTEPY6AVV5W',
                            'TMLPJNNLCZHL',
                            'TM8CYXUZEE5J',
                            'TM3VF828R9RF',
                            'TM0VFMSRHQUW',
                            'TMPSJGIR44U2',
                            'TMYDJZT7Q4T3',
                            'TM42HZ8X9U8C',
                            'TMV2OU5U9ADP',
                            'TM2PYM45I2TM'
                        ]:  # mensual
                    date_time_obj = date_time_obj + timedelta(days=30)
                    return date_time_obj.strftime("%m/%d/%Y %H:%M")
                elif term_id in ['TMQ3CB27HR2M', 'TMFVD7WS13Q6']:  # trimestral
                    date_time_obj = date_time_obj + timedelta(days=90)
                    return date_time_obj.strftime("%m/%d/%Y %H:%M")
                elif term_id in [
                    'TM7G2TN8N4D2',
                    'TMSUQW75VXLA',
                    'TMHDKJYX1KDP',
                    'TMQOLTGNU6YK',
                    'TME2MLFL7XF7',
                    'TMKHSSJD4R2W',
                    'TMII7KYZGOPD',
                    'TMQIXAFMVS52',
                    'TMEP01ABPD3B']:  # semetral
                    date_time_obj = date_time_obj + timedelta(days=180)
                    return date_time_obj.strftime("%m/%d/%Y %H:%M")
                elif term_id in [
                    'TMYRU1VPC9UJ',
                    'TM3JMVV96O9Z',
                    'TMZZ51MD7ZEX',
                    'TMJRKDT605N3',
                    'TMQZQ1RMC7X5',
                    'TM9MVY0XGWZQ',
                    'TMJLQCQ5ARWU',
                    'TMPZM28PQ4K8',
                    'TMJYNZ6YB465',
                    'TM581FYTDME6',
                    'TMHRW1JUXSQ7',
                    'TMVDCLW9PFHD',
                    'TM470583B628',
                    'TMDEYTLHKALL',
                    'TMRQ5RDPW80R',
                    'TMOPLXJB913R',
                    'TM4XUL7S97WG',
                    'TMTMSPIOHT2L',
                    'TMFG8GXBG4YQ',
                    'TM2N4XORTEFP',
                    'TMJBG8X5GVI7',
                    'TMT7X8L4O43K',
                    'TMAT7EFBV8AG',
                    'TMYO5COQ49VB',
                    'TMB27UV9E63S',
                    'TMX415TO8OET']:  # anual
                    date_time_obj = date_time_obj + timedelta(days=365)
                    return date_time_obj.strftime("%m/%d/%Y %H:%M")
                else:
                    return None

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration/'
        rama = options['rama']
        brand = options.get('site')

        name_file_migration_subscriptions = '/home/milei/Escritorio/reporte_erick/final.csv'.format(
            brand_id=settings.PIANO_APPLICATION_ID[brand],
            path=path,
            rama=rama,
            brand=brand
        )

        with open(name_file_migration_subscriptions, 'a', encoding="utf-8") as csvFilewrite:
            writer = csv.writer(csvFilewrite)
            writer.writerow(
                [
                    'user_id',
                    'subscription_id',
                    'term_id',
                    'next_billing_date'
                ]
            )

            with open('/home/milei/Escritorio/reporte_erick/dates.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('next_billing_date'):
                        next_billing_date = self.update_next_billing_date(
                            row.get('term_id'),
                            row.get('next_billing_date')
                        )
                    if next_billing_date:
                        writer.writerow(
                            [
                                row.get('user_id'),
                                row.get('subscription_id'),
                                row.get('term_id'),
                                next_billing_date
                            ]
                        )
            csvfile.close()
        print('Termino la ejecucion del comando')
