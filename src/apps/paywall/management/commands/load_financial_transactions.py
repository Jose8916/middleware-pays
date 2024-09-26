from datetime import datetime, timedelta
import time

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from sentry_sdk import capture_message, capture_exception
from urllib.parse import urljoin
import requests

from apps.paywall.models import FinancialTransaction, Payment
from apps.paywall.classes.event_report import EventReportClass
from apps.paywall.utils import utc_to_lima_time_zone
from apps.paywall.arc_clients import ReportClient


class Command(BaseCommand):
    help = 'Load Financial Transactions'
    # fecha de inicio: 2019-07-09(año - mes - dia)
    # fecha de fin: 2019-07-10(año - mes - dia)

    # python3 manage.py load_financial_transactions  --startDate "2019-08-01" --endDate "2019-08-02" --site "gestion"  #por rango de fechas
    # python3 manage.py load_financial_transactions  --startDate "2021-10-27" --endDate "2021-10-29" --site "gestion" --time_sleep 160 --report_type subscription-event
    # python3 manage.py load_financial_transactions  --hoursAgo 3  --site "gestion"  #hace 3 horas, en formato UTC
    # python3 manage.py load_report_arc  --lastDay  #hace 1 dia
    # python3 manage.py load_financial_transactions  --hoursAgo 3  --site "gestion" --report_type subscription-event

    def report_post(self, startDate, endDate, site, report_type):
        if not report_type:
            report_type = "financial-report"

        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': '' + str(site)
        }

        payload = {
            "name": "financial_transactions_report",
            "startDate": startDate + "T00:00:00.000Z",
            "endDate": endDate + "T00:00:00.000Z",
            "reportType": report_type,
            "reportFormat": "json"
        }

        url = urljoin(settings.PAYWALL_ARC_URL, 'sales/api/v1/report/schedule')
        try:
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            return result
        except Exception:
            print('Error en en API de reportes Financial Transactions ARC')
            return ""


    def report_post_last_day(self, hoursAgo):
        # datetime.datetime.now()
        # print(datetime.utcnow())
        startDate = datetime.utcnow() - timedelta(hours=int(hoursAgo))
        startDate_point = str(startDate).split('.')
        startDate_list = startDate_point[0].split(' ')

        endDate = datetime.utcnow()
        endDate_point = str(endDate).split('.')
        endDate_list = endDate_point[0].split(' ')

        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
        }

        payload = {
            "name": "reporte_arc",
            "startDate": startDate_list[0] + "T" + startDate_list[1] + ".000Z",
            "endDate": endDate_list[0] + "T" + endDate_list[1] + ".000Z",
            "reportType": "sign-up-summary",
            "reportFormat": "json"
        }
        url = urljoin(settings.PAYWALL_ARC_URL, 'identity/api/v1/report/schedule')
        try:
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            return result
        except Exception:
            print('Error en en API de reportes de ARC')
            return ""

    def report_post_last_hours(self, hoursAgo, site, report_type):
        if not report_type:
            report_type = "financial-report"

        startDate = datetime.utcnow() - timedelta(hours=int(hoursAgo))
        startDate_point = str(startDate).split('.')
        startDate_list = startDate_point[0].split(' ')

        endDate = datetime.utcnow()
        endDate_point = str(endDate).split('.')
        endDate_list = endDate_point[0].split(' ')

        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': '' + str(site)
        }

        payload = {
            "name": "reporte_arc",
            "startDate": startDate_list[0] + "T" + startDate_list[1] + ".000Z",
            "endDate": endDate_list[0] + "T" + endDate_list[1] + ".000Z",
            "reportType": report_type,
            "reportFormat": "json"
        }

        url = urljoin(settings.PAYWALL_ARC_URL, 'sales/api/v1/report/schedule')
        """
        email = EmailMessage(
            subject='cron de arc transactions',
            body='<html><body>Se ejecuto el comando para obtener el orderid y transaction id</body></html>',
            from_email=settings.PAYWALL_MAILING_SENDER,
            to=['jmachicado@rmgperustaff.com'],
        )

        email.content_subtype = "html"

        try:
            email.send(fail_silently=True)

        except (Exception, SystemExit):
            capture_exception()
        """
        try:
            response = requests.post(url, json=payload, headers=headers)
            result = response.json()
            return result
        except Exception:
            capture_exception()
            print('Error en en API de reportes de ARC')
            return ""

    def report_download(self, jobid, site):
        url = settings.PAYWALL_ARC_URL + "sales/api/v1/report/" + str(jobid) + "/download"

        payload = ""
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer " + settings.PAYWALL_ARC_TOKEN,
            'cache-control': "no-cache",
            'Arc-Site': '' + str(site)
        }

        response = requests.request("GET", url, data=payload, headers=headers)
        if response.status_code == 200:
            for obj in response.json():
                if not FinancialTransaction.objects.filter(
                    provider_reference=obj.get('providerReference')
                ).exists():

                    try:
                        if site:
                            if site == 'gestion':
                                nrosite = '1'
                            elif site == 'elcomercio':
                                nrosite = '2'
                            else:
                                nrosite = ''

                        if obj.get('providerReference', ''):
                            provider_reference = obj.get('providerReference', '')
                            prov_reference = provider_reference.split('~')

                        financial_transaction = FinancialTransaction(
                            country=obj.get('country', ''),
                            last_name=obj.get('lastName', ''),
                            second_last_name=obj.get('secondLastName', ''),
                            amount=obj.get('amount', ''),
                            order_number=obj.get('orderNumber', ''),
                            client_id=obj.get('clientId', ''),
                            locality=obj.get('locality', ''),
                            tax=obj.get('tax', ''),
                            financial_transaction_id=obj.get('financialTransactionId', ''),
                            transaction_type=obj.get('transactionType', ''),
                            first_name=obj.get('firstName', ''),
                            initial_transaction=obj.get('initialTransaction', ''),
                            provider_reference=obj.get('providerReference', ''),
                            currency=obj.get('currency', ''),
                            postal=obj.get('postal', ''),
                            region=obj.get('region', ''),
                            subscription_id=obj.get('subscriptionId', ''),
                            sku=obj.get('sku', ''),
                            line_two=obj.get('line2', ''),
                            line_one=obj.get('line1', ''),
                            data=obj,
                            order_id=prov_reference[0],
                            transaction_id=prov_reference[1],
                            site=nrosite,
                        )
                        if utc_to_lima_time_zone(obj.get('periodTo', '')):
                            financial_transaction.period_to = utc_to_lima_time_zone(obj.get('periodTo', ''))

                        if utc_to_lima_time_zone(obj.get('periodFrom', '')):
                            financial_transaction.period_from = utc_to_lima_time_zone(obj.get('periodFrom', ''))

                        if utc_to_lima_time_zone(obj.get('createdOn', '')):
                            financial_transaction.created_on = utc_to_lima_time_zone(obj.get('createdOn', ''))

                        financial_transaction.save()
                        try:
                            payment = Payment.objects.get(arc_order=obj.get('orderNumber', ''))
                        except Exception:
                            payment = None
                        if payment:
                            payment.payu_transaction = prov_reference[1]
                            payment.save()
                    except Exception:
                        capture_exception()

            return True
        else:
            capture_message('load_financial_transactions.report_download: Timeout')
            return False

    def add_arguments(self, parser):
        parser.add_argument('--startDate', nargs='?', type=str)
        parser.add_argument('--endDate', nargs='?', type=str)
        parser.add_argument('--hoursAgo', nargs='?', type=str)
        parser.add_argument('--site', nargs='?', type=str)
        parser.add_argument('--time_sleep', nargs='?', type=str)
        parser.add_argument('--long_time', nargs='?', type=str)
        parser.add_argument('--report_type', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('long_time'):
            list_days = [
                {"start_date": "2021-09-24", "end_date": "2021-09-29"},
                {"start_date": "2021-09-29", "end_date": "2021-10-03"},
                {"start_date": "2021-10-03", "end_date": "2021-10-08"},
                {"start_date": "2021-10-08", "end_date": "2021-10-13"},
                {"start_date": "2021-10-13", "end_date": "2021-10-15"}
            ]
            list_brand = ['elcomercio', 'gestion']
            for o_day in list_days:
                for brand in list_brand:
                    print("{} . {} . {}".format(o_day.get('start_date'), o_day.get('end_date'), brand))
                    report_response = self.report_post(o_day.get('start_date'), o_day.get('end_date'), brand)
                    if report_response:
                        jobid = report_response.get('jobID', '')
                        if options.get('time_sleep', None):
                            time.sleep(int(options.get('time_sleep')))
                        else:
                            time.sleep(120)
                        if self.report_download(jobid, brand):
                            print('Completed ' + str(jobid))
                        else:
                            print('Hubo un problema al descargar')
                    else:
                        print('primer servicio no responde')
            return 'Completed'

        if options.get('startDate') and options.get('endDate') and options.get('site'):
            report_response = self.report_post(
                options.get('startDate'),
                options.get('endDate'),
                options.get('site'),
                options.get('report_type', '')
            )
            if report_response:
                jobid = report_response.get('jobID', '')
                if options.get('time_sleep', None):
                    time.sleep(int(options.get('time_sleep')))
                else:
                    time.sleep(120)

                if options.get('report_type', '') == 'subscription-event':
                    events = ReportClient().get_sales(jobid, options.get('site'))
                    event_report = EventReportClass()
                    event_report.save_event_report(events, options.get('site'))
                else:
                    if self.report_download(jobid, options.get('site')):
                        return 'Completed'
                    else:
                        return 'Hubo un problema al descargar'
            else:
                return 'hubo un problema'
        if options.get('hoursAgo') and options.get('site'):
            first_step_report = self.report_post_last_hours(
                options.get('hoursAgo'),
                options.get('site'),
                options.get('report_type', '')
            )
            if first_step_report:
                jobid = first_step_report.get('jobID', '')
                time.sleep(130)
                if options.get('report_type', '') == 'subscription-event':
                    events = ReportClient().get_sales(jobid, options.get('site'))
                    event_report = EventReportClass()
                    event_report.save_event_report(events, options.get('site'))
                else:
                    if self.report_download(jobid, options.get('site')):
                        return 'Completed'
                    else:
                        return 'Hubo un problema al descargar'
            else:
                return 'hubo un problema'
        else:
            print('python3 manage.py load_financial_transactions --startDate "2019-08-01" --endDate "2019-08-02" --site "gestion"')
            print('python3 manage.py load_financial_transactions  --hoursAgo 3  --site "gestion"')

