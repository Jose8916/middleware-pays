from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, PaymentTracking, Payment


class Command(BaseCommand):
    help = 'A la tabla de tracking vincula o desvincula una subscripcion'
    # python manage.py unlinktracking --arc_order 2NYOMQM9TVWP4EL1 --truncate_subscription 1
    # python manage.py unlinktracking --arc_order 2NYOMQM9TVWP4EL1 --subscription_id 5517224031562407

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--truncate_subscription', nargs='?', type=str)
        parser.add_argument('--arc_order', nargs='?', type=str)

    def handle(self, *args, **options):
        # Desvincula una susbscripcion a tracking
        if options.get('arc_order') and options.get('truncate_subscription'):
            payment_tracking = PaymentTracking.objects.filter(
                arc_order=options.get('arc_order')
            ).update(
                subscription=None,
                payment=None
            )
            print('actualizacion realizada correctamente')

        # Vincula una susbscripcion a tracking

        if options.get('arc_order') and options.get('subscription_id'):
            subscription = Subscription.objects.get(arc_id=options.get('subscription_id'))
            payment = Payment.objects.get(arc_order=options.get('arc_order'))
            payment_tracking = PaymentTracking.objects.filter(
                arc_order=options.get('arc_order')
            ).update(
                subscription=subscription,
                payment=payment
            )
            print('actualizacion realizada correctamente')
