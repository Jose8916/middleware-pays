import json
import requests
import json, csv, time, os, fnmatch
from django.utils.encoding import smart_str
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, FinancialTransaction


class Command(BaseCommand):
    help = 'Este comando carga el historial de deliverys'
    """
        python3 manage.py load_deliverys
    """

    def get_siebel_delivery(self, subscription):
        try:
            suscripcion_obj = Subscription.objects.get(arc_id=subscription)
            if suscripcion_obj:
                return suscripcion_obj.delivery
            else:
                return ''
        except Exception as e:
            return ''

    def handle(self, *args, **options):
        with open('/tmp/lista_delivery.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([
                smart_str(u"transactionId"),
                smart_str(u"Delivery")
            ])
            name = '/tmp/data_report.csv'
            with open(name) as csvfile:
                reader = csv.reader(csvfile, delimiter=",")
                for row in reader:
                    try:
                        transaction = FinancialTransaction.objects.get(transaction_id=str(row[0]))
                        delivery = self.get_siebel_delivery(transaction.subscription_id)
                        fila = [
                            row[0],
                            delivery
                        ]
                        writer.writerow(fila)
                    except Exception:
                        continue

            csvFile.close()

