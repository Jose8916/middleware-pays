from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.paywall.utilsfunctions.dates import get_yesterday
from django.db.models import Q
import requests
import json, csv, time, os, fnmatch

from sentry_sdk import capture_event, capture_exception


class Command(BaseCommand):
    help = 'Registra en google drive las ventas extraidas del api de digitales'
    hash = int(time.time())
    # python3 manage.py register_history_sales_api_dwh --get_yesterday 1

    def add_arguments(self, parser):
        parser.add_argument('--get_yesterday', nargs='?', type=str)

    def get_api_dwh_digitales(self, start_day, end_day, page=None):
        lista = None
        data = {"date_start": start_day, "date_end": end_day}
        if page:
            url = 'https://paywall.comerciosuscripciones.pe/api/user-subscriptions/?page='+str(page)
        else:
            url = 'https://paywall.comerciosuscripciones.pe/api/user-subscriptions/'
        headers = {'content-type': 'application/json',
                   'Authorization': 'Token 5088cbc5ceb807c702b4e3487173ef792eb50be4'}
        try:
            r = requests.post(url, json=data, headers=headers)
            lista = r.json()
        except Exception as e:
            print('error al obtener data')
            print(e)
            capture_exception()
        except SystemExit:
            print(e)
            capture_exception()
        return lista

    def write_csv(self, list_sales, page=None):
        count = 1
        keys_list = []
        if page:
            name = '/tmp/data_report_' + str(get_yesterday()) + 'page' + str(page) + '_' + str(self.hash) + '.csv'
        else:
            name = '/tmp/data_report_' + str(get_yesterday()) + '_' + str(self.hash) + '.csv'

        with open(name, 'a') as csvFile:
            writer = csv.writer(csvFile)
            for obj in list_sales:
                if count == 1:
                    keys_list = list(obj.keys())
                    writer.writerow(keys_list)
                    count = count + 1
                row = []
                for name_dict in keys_list:
                    row.append(obj.get(name_dict, ''))
                writer.writerow(row)
            csvFile.close()

    def read_csv_files(self, number):
        list_dicts = []

        for i in range(number):
            name = '/tmp/data_report_' + str(get_yesterday()) + 'page' + str(i) + '_' + str(self.hash) + '.csv'
            try:
                with open(name) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        list_dicts.append(row)
            except Exception as e:
                print(e)
                capture_exception()
                break
        return list_dicts

    def write_join_csv(self, list_dicts):
        count = 1
        keys_list = []
        with open('/tmp/data_report_' + str(get_yesterday()) + '_' + str(self.hash) + '.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            for obj in list_dicts:
                if count == 1:
                    keys_list = list(obj.keys())
                    writer.writerow(keys_list)
                    count = count + 1
                row = []
                for name_dict in keys_list:
                    row.append(obj.get(name_dict, ''))
                writer.writerow(row)
            csvFile.close()

    def delete_file(self):
        name = '/tmp/data_report_' + str(get_yesterday()) + '_' + str(self.hash) + '.csv'

        if os.path.exists(name):
            try:
                os.remove(name)
            except Exception as e:
                print('no pudo eliminar el archivo' + name)
                capture_exception()
        else:
            print("The file does not exist")

    def write_in_gooogle(self, name):
        headers = {
            "Authorization": "Bearer ya29.a0AfH6SMBvZLBh4hazFF-sEBhJ9h3WkNXRBoijddOiUW5GLYCH6d2-L7bKro0ThrhYqNVOmtt4hnpCe-fk0qthTKtbX1MMZ7IH78kwqbKgOw7nw3XKFRghGS7ZBQ7cmDr0NuiiQflJKaI_oqtcjsF0Rlh8okFt7J-PqUehIcwJHNY"}
        data = {
            "name": name,
            "parents": ["1rcPmBPNXfmrpGj35IfP_Fdn2pSMQDXiz"]
        }
        files = {
            'data': ('metadata', json.dumps(data), 'application/json; charset=UTF-8'),
            'file': open("/tmp/" + name, "rb")
        }
        try:
            r = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers=headers,
                files=files
            )
            print(r.text)
            return r.text
        except Exception as e:
            print(e)
            capture_exception()

    def handle(self, *args, **options):
        if options.get('get_yesterday'):
            list_sales = self.get_api_dwh_digitales(get_yesterday(), get_yesterday()) # obtiene las suscripciones del API de ventas

            if list_sales:
                self.write_csv(list_sales)
            elif not list_sales:
                # self.delete_file()
                for i in range(1000):
                    i = i + 1
                    list_sales = self.get_api_dwh_digitales(get_yesterday(), get_yesterday(), i)
                    if list_sales:
                        self.write_csv(list_sales, i)
                        time.sleep(2)
                    else:
                        break
                # Une los archivos csv a uno solo
                list_dicts = self.read_csv_files(i)
                if list_dicts:
                    self.write_join_csv(list_dicts)

            name = 'data_report_' + str(get_yesterday()) + '_' + str(self.hash) + '.csv'

            if os.path.exists('/tmp/' + name):
                print('ingessa')
                self.write_in_gooogle(name)
            else:
                print('no existe')
                print(name)





