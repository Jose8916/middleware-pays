from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, LowBySuspension, EventTypeSuspension
import pytz

TIMEZONE = pytz.timezone('America/Lima')


class Command(BaseCommand):
    help = 'llena la tabla de bajas por suspencion(LowBySuspension)'
    # python3 manage.py add_low_by_suspension --all 1
    # python3 manage.py add_low_by_suspension --month 11/2020
    # python3 manage.py add_low_by_suspension --last_days 2

    def add_arguments(self, parser):
        parser.add_argument('--all', nargs='?', type=str)
        parser.add_argument('--truncate', nargs='?', type=str)
        parser.add_argument('--month', nargs='?', type=str)
        parser.add_argument('--last_days', nargs='?', type=str)

    def handle(self, *args, **options):
        count = 0
        if options.get('truncate'):
            EventTypeSuspension.objects.all().delete()
            LowBySuspension.objects.all().delete()

        if options.get('all'):
            subscriptions = Subscription.objects.filter(
                state=Subscription.ARC_STATE_TERMINATED,
                data__currentPaymentMethod__paymentPartner__contains="PayULATAM"
            )

        if options.get('month', ''):
            date_query = options.get('month', '')
            date_query = datetime.strptime(date_query, '%m/%Y')
            subscriptions = Subscription.objects.filter(
                state=Subscription.ARC_STATE_TERMINATED,
                date_anulled__month=date_query.month,
                date_anulled__year=date_query.year,
                data__currentPaymentMethod__paymentPartner__contains="PayULATAM"
            )

        if options.get('last_days', ''):
            number_of_days = options.get('last_days', '')
            start_date = datetime.now(TIMEZONE) - timedelta(days=int(number_of_days))
            end_date = datetime.now(TIMEZONE)
            subscriptions = Subscription.objects.filter(
                state=Subscription.ARC_STATE_TERMINATED,
                date_anulled__range=self.range_to_timestamp(start_date, end_date),
                data__currentPaymentMethod__paymentPartner__contains="PayULATAM"
            )

        for subscription in subscriptions:
            if not LowBySuspension.objects.filter(subscription=subscription).exists():
                try:
                    events = subscription.data.get('events', '')
                except Exception:
                    events = ''

                if events:
                    ordered_events = sorted(events, key=lambda i: i['eventDateUTC'])
                    total = len(ordered_events) - 1
                    penultimate_event = ordered_events[total - 1]
                    if penultimate_event:
                        if 'FAIL_RENEW_SUBSCRIPTION' in penultimate_event.get('eventType', ''):
                            event_content = penultimate_event.get('details', '')
                            event_content_list = event_content.split("-")
                            try:
                                name_event = event_content_list[0]
                            except Exception:
                                name_event = ''

                            try:
                                detail_event = event_content_list[1]
                            except Exception:
                                detail_event = ''

                            if not EventTypeSuspension.objects.filter(name=name_event).exists():
                                event_type = EventTypeSuspension(
                                    name=name_event
                                )
                                event_type.save()

                            low_by_suspension = LowBySuspension(
                                subscription=subscription,
                                event_type=name_event,
                                detail=detail_event
                            )
                            low_by_suspension.save()

                            count = count + 1

        print('Se actualizaron ' + str(count) + ' registros')