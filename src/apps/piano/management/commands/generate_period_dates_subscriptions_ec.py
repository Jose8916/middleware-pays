
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import csv


class Command(BaseCommand):
    help = 'genera el archivo de fechas de acceso de elcomercio'
    """
        python3 manage.py generate_period_dates_subscriptions_ec --brand 'elcomercio'
    """
    def add_arguments(self, parser):
        parser.add_argument('--compara_fecha_inicio_con_next_billing_date', nargs='?', type=str)
        parser.add_argument('--brand', nargs='?', type=str)

    def get_time(self, payment):
        return payment.get('period_from_timestamp')

    def get_format_date(self, date_to_split):
        list_date = date_to_split.split("/")
        if len(list_date[2]) == 2:
            return list_date[0] + '/' + list_date[1] + '/20' + list_date[2]
        return date_to_split

    def get_split_date(self, date_to_split):
        split_date = date_to_split.split(" ")
        return split_date[1]

    def update_to_timestamp(self, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = int(datetime.strptime(date_to_update, "%m/%d/%Y").timestamp())
        return date_time_obj

    def compare_dates(self, next_billing_date, fecha_de_inicio_piano):
        if next_billing_date and fecha_de_inicio_piano:
            next_billing_date_obj = datetime.strptime(next_billing_date, "%Y-%m-%d %H:%M:%S")
            fecha_de_inicio_piano_obj = datetime.strptime(fecha_de_inicio_piano, "%Y-%m-%d %H:%M")
            if next_billing_date_obj.day != fecha_de_inicio_piano_obj.day:
                return True
            else:
                return False
        else:
            False

    def generate_period_dates(self, term_id, date_to_update):
        # '04/19/2022 11:23'
        date_time_obj = datetime.strptime(date_to_update, "%m/%d/%Y %H:%M")

        if term_id in \
                [
                    'TM3IS6EOZNBY',
                    'TMXS6861CIC9',
                    'TM5LUOGA55OH',
                    'TM2GH0RSSJLU',
                    'TMYL2LFUJ1QE',
                    'TM5TFAAGUCIT',
                    'TMZAN6CQ9K6Q',
                    'TMWT8W8HLMK2',
                    'TMLW4S43PXO6',
                    'TMS8FP7VOPTU',
                    'TMXJJKT70CYE',
                    'TMYXTFSP1YAH',
                    'TMOYNXTMZBV9',
                    'TM0JBFKUSGT7',
                    'TMJKC9YEZU4V',
                    'TMP5XRJOP4EL',
                    'TM551L5XD41K',
                    'TMCH51GISE16',
                    'TM9HCSXAO17L',
                    'TMVHZQJN8ZSU',
                    'TMHIOHVXKNLY',
                    'TMACBXZMFODO',
                    'TMCQEKWYN4C7',
                    'TMZIHFBK4H01',
                    'TMPAARD8O89P',
                    'TME92OG2538B',
                    'TM56ZD4IVCEF',
                    'TMQAZ3UZP7IT',
                    'TMEL3GQ893NR',
                    'TMOC7LW3XM5Z',
                    'TMOB6VXNK2HH',
                    'TM4YPNW5NJ08',
                    'TMJGUYRE55XF',
                    'TMQ5TD8O3GSC',
                    'TMPOJDDKQUM3',
                    'TMAS4QP632C9',
                    'TMPOY7UP7W83',
                    'TMFP76TBLC85',
                    'TMGIOT6X24NN'
                ]:  # mensual

            period_to_date_time_obj = date_time_obj + relativedelta(months=1)

            return date_time_obj.strftime("%m/%d/%Y"), period_to_date_time_obj.strftime("%m/%d/%Y")
        elif term_id in ['TM93F79NQKV7', 'TMKG41DF25CZ', 'TMAK8ZEK10WH', 'TM8OKYPIPMT6', 'TMGM0F7MK839']:  # trimestral
            period_to = date_time_obj + relativedelta(months=3)
            return date_time_obj.strftime("%m/%d/%Y"), period_to.strftime("%m/%d/%Y")
        elif term_id in [
            'TM7HO3UACZGI',
            'TMCFO5PKUVSZ',
            'TM4A7V80H4AR',
            'TM8AXAYHVHDC',
            'TMC4HG88FDRU',
            'TMEBZIWHYHEH',
            'TMORAMGG1JO7'
        ]:  # semetral
            period_from = date_time_obj
            period_to_date_time_obj = date_time_obj + relativedelta(months=6)

            return period_from.strftime("%m/%d/%Y"), period_to_date_time_obj.strftime("%m/%d/%Y")
        elif term_id in [
            'TMIFDEUDT7MG',
            'TMWS3KI3PFSQ',
            'TMNU44NTAZFJ',
            'TMV5YR98P5IK',
            'TMXI7PHXWDN7',
            'TMH1UE42Q3G3',
            'TMR4FFJ9MLEH',
            'TMC8SG6W82GC',
            'TM3IZZ8ELB94',
            'TMLOIQYFZX04',
            'TM1TEEAQMOVB',
            'TMUCKHXRY3MG',
            'TM85IOFRZVOJ',
            'TMYKKS813SYK',
            'TMXE7XP7SYVK',
            'TM6EN0TL77ME',
            'TMSAWFZWW1C6',
            'TMNXAXUANTJR',

        ]:  # anual
            period_to = date_time_obj + relativedelta(years=1)
            return date_time_obj.strftime("%m/%d/%Y"), period_to.strftime("%m/%d/%Y")
        else:
            return None

    def handle(self, *args, **options):
        brand = options.get('brand')
        path_source = '/home/milei/Documentos/subscription_migration/production_' + brand + '/backup/update/'
        if options['compara_fecha_inicio_con_next_billing_date']:
            list_subs_piano = []
            with open(path_source) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('Subscription ID', '') not in list_subs_piano:
                        list_subs_piano.append(row.get('Subscription ID', ''))
                        if self.compare_dates(row.get('Next Billing Date'), row.get('fecha_de_inicio_piano')):
                            print(row.get('Subscription ID', ''))
            csvfile.close()
        else:
            list_subs = []
            list_user_exclude = []

            with open(path_source + 'archivo_base.csv') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('arc_subs_id') == '#N/D':
                        list_user_exclude.append(row.get('User ID (UID)'))
                        continue

                    if row.get('Tx Type') == 'refund' or row.get('Status') == 'refunded' or row.get('User ID (UID)') in list_user_exclude:
                        continue

                    ingresa = True
                    for item in list_subs:
                        if item.get('subscription_id') == row.get('Subscription ID', ''):
                            for item_pay in item.get('payments'):
                                if item_pay.get('ex_tx_id') != row.get('External Tx ID', ''):
                                    list_payments = item.get('payments')
                                    dict_payment = {
                                        'ex_tx_id': row.get('External Tx ID', ''),
                                        'period_from': self.get_format_date(row.get('access from', '')),
                                        'period_from_timestamp': self.update_to_timestamp(self.get_format_date(row.get('access from', ''))),
                                        'period_to': self.get_format_date(row.get('access to', ''))
                                    }
                                    list_payments.append(dict_payment)
                                    item['payments'] = list_payments
                                    ingresa = False
                                    break

                    # crea la lista de suscripciones
                    if not list_subs or ingresa:
                        list_payments = {}
                        sub_obj = {}
                        next_billing_date_arc = row.get('next_billing_date_arc', '')
                        list_payments['ex_tx_id'] = row.get('External Tx ID', '')
                        list_payments['period_from'] = self.get_format_date(row.get('access from', ''))
                        list_payments['period_from_timestamp'] = self.update_to_timestamp(self.get_format_date(row.get('access from', '')))
                        list_payments['period_to'] = self.get_format_date(row.get('access to', ''))
                        sub_obj['subscription_id'] = row.get('Subscription ID', '')
                        sub_obj['term_id'] = row.get('Term ID', '')
                        sub_obj['next_billing_date_arc'] = next_billing_date_arc.replace('"', '')
                        sub_obj['payments'] = [list_payments]
                        list_subs.append(sub_obj)

            list_subs_test = [
                {
                    'subscription': 'jdjdj',
                    'payments': [
                        {
                            "ex_tx_id": "kkkkkkk",
                            "period_from": "dfecha",
                            "period_to": "dfecha",
                            "period_from_timestamp": "dfecha",
                        },
                        {
                            "ex_tx_id": "kkkkkkk",
                            "period_from": "dfecha",
                            "period_to": "dfecha"
                        }
                    ]
                },
                {
                    'subscription': 'jdjdj',
                    'term_id': 'sss',
                    'next_billing_date_arc': 'date',
                    'payments': [
                        {
                            "ex_tx_id": "kkkkkkk",
                            "period_from": "dfecha",
                            "period_to": "dfecha"
                        },
                        {
                            "ex_tx_id": "kkkkkkk",
                            "period_from": "dfecha",
                            "period_to": "dfecha"
                        }
                    ]
                }
            ]

            with open(path_source + '/fechas_corregidas_piano.csv', 'a', encoding="utf-8") as csvFilewrite:
                writer = csv.writer(csvFilewrite)
                writer.writerow(
                    [
                        'suscripcion',
                        'External Tx ID',
                        'period_from',
                        'period_to'
                    ]
                )
                for row in list_subs:
                    if row.get('subscription_id') == 'RCYKV8JB1HGU':
                        print(row)
                    list_payments_ = row.get('payments')
                    period_from = False

                    list_payments_.sort(key=self.get_time)
                    minutos = ''
                    for row_pay in list_payments_:
                        if period_from:
                            from_date = period_to + ' ' + minutos
                        else:
                            from_date = row.get('next_billing_date_arc')
                            minutos = self.get_split_date(row.get('next_billing_date_arc'))
                        print('-------')
                        print(row_pay.get('ex_tx_id'))
                        print('-------')
                        period_from, period_to = self.generate_period_dates(
                            row.get('term_id'),
                            from_date
                        )
                        if row.get('subscription_id') == 'RCYKV8JB1HGU':
                            print(period_from)
                            print(row_pay.get('access from'))
                            print('----')
                        if period_from == row_pay.get('period_from') and period_to == row_pay.get('period_to'):
                            # extid correcto
                            print(row_pay.get('ex_tx_id'))
                            break
                        else:
                            writer.writerow(
                                [
                                     row.get('subscription_id'),
                                     row_pay.get('ex_tx_id'),
                                     period_from,
                                     period_to
                                ]
                            )
        return 'completado'
