from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, TypeOfLowSubscription
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_message, capture_exception, capture_event
import pytz

TIMEZONE = pytz.timezone('America/Lima')


class Command(BaseCommand):
    help = 'Llena los tipos de baja en la tabla LowBySuspension'
    # python3 manage.py add_type_of_low --month 02/2021
    # python3 manage.py add_type_of_low --all 1
    # python3 manage.py add_type_of_low --last_days 2

    def add_arguments(self, parser):
        parser.add_argument('--all', nargs='?', type=str)
        parser.add_argument('--truncate', nargs='?', type=str)
        parser.add_argument('--month', nargs='?', type=str)
        parser.add_argument('--last_days', nargs='?', type=str)

    def start_day(self, start_date):
        starts = datetime.combine(
            start_date,
            datetime.min.time()
        )
        return get_default_timezone().localize(starts)

    def end_day(self, end_date):
        ends = datetime.combine(
            end_date,
            datetime.max.time()
        )
        return get_default_timezone().localize(ends)

    def handle(self, *args, **options):
        if options.get('truncate'):
            TypeOfLowSubscription.objects.all().delete()

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
            if not TypeOfLowSubscription.objects.filter(subscription=subscription).exists():
                try:
                    events = subscription.data.get('events', '')
                except Exception:
                    events = ''

                if events:
                    ordered_events = sorted(events, key=lambda i: i['eventDateUTC'])
                    total = len(ordered_events) - 1
                    penultimate_event = ordered_events[total - 1]
                    if penultimate_event:
                        list_suspend = ['SUSPEND_SUBSCRIPTION', 'FAIL_RENEW_SUBSCRIPTION']

                        if penultimate_event.get('eventType', '') in list_suspend:
                            type_of_low = TypeOfLowSubscription(
                                subscription=subscription,
                                type=TypeOfLowSubscription.LOW_BY_SUSPENSION
                            )
                            type_of_low.save()

                        elif penultimate_event.get('eventType', '') == 'CANCEL_SUBSCRIPTION':
                            type_of_low = TypeOfLowSubscription(
                                subscription=subscription,
                                type=TypeOfLowSubscription.LOW_BY_CANCELLATION
                            )
                            type_of_low.save()

                        elif penultimate_event.get('eventType', '') in \
                                ['START_SUBSCRIPTION', 'RENEW_SUBSCRIPTION', 'UPDATE_PAYMENT_METHOD']:
                            type_of_low = TypeOfLowSubscription(
                                subscription=subscription,
                                type=TypeOfLowSubscription.LOW_BY_ADMIN
                            )
                            type_of_low.save()
                        else:
                            print('Un nuevo caso:' + str(subscription))
                            capture_event(
                                {
                                    'message': 'Tipo de baja no detectado',
                                    'extra': {
                                        'suscripcion': subscription,
                                    }
                                }
                            )

        print('Operacion exitosa')
