import json
import csv
from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.utils.encoding import smart_str
from django.utils import formats, timezone
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception
from apps.paywall.models import Subscription
from django.conf import settings


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def start_date(self, date_start):
        start = datetime.combine(
            datetime.strptime(date_start, "%Y-%m-%d"),
            datetime.min.time()
        )
        return get_default_timezone().localize(start)

    def end_date(self, date_end):
        end = datetime.combine(
            datetime.strptime(date_end, "%Y-%m-%d"),
            datetime.max.time()
        )
        return get_default_timezone().localize(end)

    def handle(self, *args, **options):
        """
        Retorna las suscripciones pagadas por payu

        Parámetros:
        - date_start: Fecha de inicio en formato %Y-%m-%d
        - date_end: Fecha de fin en formato %Y-%m-%d
        """

        tz = timezone.get_current_timezone()
        with open('/tmp/suscripciones.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([
                smart_str(u"Marca"),
                smart_str(u"Plan"),
                smart_str(u"Price Code"),
                smart_str(u"SKU"),
                smart_str(u"Plan"),
                smart_str(u"UUID"),
                smart_str(u"Fecha de baja"),
                smart_str(u"Fecha de alta"),
                smart_str(u"Delivery"),
                smart_str(u"Nombre"),
                smart_str(u"Tipo de documento"),
                smart_str(u"Documento"),
                smart_str(u"SubscriptionId"),
                smart_str(u"Estado"),
            ])

            subscription_list = Subscription.objects.all().order_by(
                'starts_date'
            )[0:20]

            for obj in subscription_list.iterator():
                if obj.by_payu_method():
                    try:
                        plan = obj.plan.plan_name
                    except Exception:
                        plan = ''

                    try:
                        marca = obj.partner.partner_name
                    except Exception:
                        marca = ''

                    try:
                        tz_date_anulled = obj.date_anulled.astimezone(tz)
                        date_anulled = formats.date_format(tz_date_anulled, settings.DATETIME_FORMAT)
                    except Exception:
                        date_anulled = ''

                    try:
                        tz_starts_date = obj.starts_date.astimezone(tz)
                        date_start_subscription = formats.date_format(tz_starts_date, settings.DATETIME_FORMAT)
                    except Exception:
                        date_start_subscription = ''

                    try:
                        uuid = obj.arc_user.uuid
                    except Exception:
                        uuid = ''

                    try:
                        delivery = obj.delivery
                    except Exception as e:
                        delivery = ''

                    try:
                        name = obj.payment_profile.get_full_name()
                    except Exception as e:
                        name = ''

                    try:
                        type_document = obj.payment_profile.prof_doc_type
                    except Exception as e:
                        type_document = ''

                    try:
                        document = obj.payment_profile.prof_doc_num
                    except Exception as e:
                        document = ''

                    try:
                        subscription_id = str(obj.arc_id) + ' '
                    except Exception as e:
                        subscription_id = ''

                    try:
                        estado = obj.get_state_display(),
                    except Exception as e:
                        estado = ''

                    writer.writerow([
                        smart_str(marca),
                        smart_str(plan),
                        smart_str(obj.data['priceCode'] if obj.data else ''),
                        smart_str(obj.data['sku'] if obj.data else ''),
                        smart_str(uuid),
                        smart_str(date_anulled),
                        smart_str(date_start_subscription),
                        smart_str(delivery or ''),
                        smart_str(name),
                        smart_str(type_document),
                        smart_str(document),
                        smart_str(subscription_id),
                        smart_str(estado)
                    ])
                    print([
                        smart_str(marca),
                        smart_str(plan),
                        smart_str(obj.data['priceCode'] if obj.data else ''),
                        smart_str(obj.data['sku'] if obj.data else ''),
                        smart_str(uuid),
                        smart_str(date_anulled),
                        smart_str(date_start_subscription),
                        smart_str(delivery or ''),
                        smart_str(name),
                        smart_str(type_document),
                        smart_str(document),
                        smart_str(subscription_id),
                        smart_str(estado)
                    ])

        csvFile.close()
        print('termino la ejecucion del comando')
