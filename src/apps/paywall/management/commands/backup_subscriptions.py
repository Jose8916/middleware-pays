# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from apps.paywall.arc_clients import ReportClient
import csv
import time


class Command(BaseCommand):
    help = 'Genera un backup de las suscripciones'
    """
        - Genera el csv AID_psc_subs.csv para la migracion de terminos de pago
        - Para los post: python3 manage.py backup_subscriptions --start_date "2019-01-01" --end_date "2022-02-15" --site "gestion" --job_id 1 --rama 'sandbox'
        - Para los get: python3 manage.py backup_subscriptions --site "gestion" --rama 'sandbox'
    """
    def add_arguments(self, parser):
        parser.add_argument('--start_date', nargs='?', type=str)
        parser.add_argument('--end_date', nargs='?', type=str)
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--job_id', nargs='?', type=str)
        parser.add_argument('--rama', nargs='?', type=str)

    def dates_format(self, date_init, date_end):
        # date_init = '2022-01-30T00:00:00Z'
        # date_end = '2018-01-30T00:00:00Z'

        di = datetime.strptime(date_init, "%Y-%m-%d")
        de = datetime.strptime(date_end, "%Y-%m-%d")

        return di, de

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration'
        path_jobs = '{path}/{rama}/jobs_{rama}.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_backup = '{path}/{rama}/backup_{rama}_delta2.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_jobs_error_get_download = '{path}/{rama}/jobs_{rama}_error_delta.csv'.format(
            path=path,
            rama=options['rama']
        )

        if options['job_id']:
            date_start, date_end = self.dates_format(options['start_date'], options["end_date"])
            total_weeks = (date_end - date_start).days // 7

            list_report = list()
            for _ in range(total_weeks):
                date_end = date_start + timedelta(days=7)
                list_report.append(
                    ReportClient().report_post(
                        date_start.strftime("%Y-%m-%d"),
                        date_end.strftime("%Y-%m-%d"),
                        options["site"],
                        'financial-report'
                    )
                )
                date_start = date_end
                time.sleep(2)

            with open(path_jobs, 'a') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(
                    [
                        'name',
                        'startDateUTC',
                        'endDateUTC',
                        'jobID',
                        'status',
                        'payload'
                    ]
                )

                for obj in list_report:
                    writer.writerow(
                        [
                            obj.get('name'),
                            obj.get('startDateUTC'),
                            obj.get('endDateUTC'),
                            obj.get('jobID'),
                            obj.get('status'),
                            obj.get('payload')
                        ]
                    )
            return 'completado'
        else:
            with open(path_backup, 'a', encoding="utf-8") as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(
                    [
                        'country',
                        'lastName',
                        'periodTo',
                        'secondLastName',
                        'amount',
                        'orderNumber',
                        'clientId',
                        'periodFrom',
                        'tax',
                        'financialTransactionId',
                        'createdOn',
                        'transactionType',
                        'firstName',
                        'initialTransaction',
                        'providerReference',
                        'currency',
                        'subscriptionId',
                        'sku',
                        'line2'
                    ]
                )
                with open(path_jobs_error_get_download, 'a') as csvFileErrorJobs:
                    with open(path_jobs) as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            list_report = ReportClient().get_sales(row[3], options["site"])
                            if list_report:
                                for obj in list_report:
                                    if obj:
                                        writer.writerow(
                                            [
                                                obj.get('country', ''),
                                                obj.get('lastName', ''),
                                                obj.get('periodTo', ''),
                                                obj.get('secondLastName', ''),
                                                obj.get('amount', ''),
                                                obj.get('orderNumber', ''),
                                                obj.get('clientId', ''),
                                                obj.get('periodFrom', ''),
                                                obj.get('tax', ''),
                                                obj.get('financialTransactionId', ''),
                                                obj.get('createdOn', ''),
                                                obj.get('transactionType', ''),
                                                obj.get('firstName', ''),
                                                obj.get('initialTransaction', ''),
                                                obj.get('providerReference', ''),
                                                obj.get('currency', ''),
                                                obj.get('subscriptionId', ''),
                                                obj.get('sku', ''),
                                                obj.get('line2', '')
                                            ]
                                        )
                            else:
                                writer_error_job = csv.writer(csvFileErrorJobs)
                                writer_error_job.writerow(['jobid', 'detalle'])
                                writer_error_job.writerow([row[3], list_report])
                                print(row[3])
                            time.sleep(2)
                csvFileErrorJobs.close()
            csvFile.close()
            return 'completado'

