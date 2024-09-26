from django.conf import settings
from django.core.management.base import BaseCommand
from apps.paywall.models import PaymentTracking, Subscription, Payment
from apps.arcsubs.models import ArcUser


class Command(BaseCommand):
    help = 'Carga data imcompleta a la tabla de PaymentTracking'
    """
        * python3 manage.py update_tracking --all 1
          carga todos los PaymentTracking que no tengan suscripcion
    """

    def add_arguments(self, parser):
        parser.add_argument('--subscription_id', nargs='?', type=str)
        parser.add_argument('--uuid', nargs='?', type=str)
        parser.add_argument('--arc_order', nargs='?', type=str)
        parser.add_argument('--all', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('all'):
            print('Id_subscriptions cargados:')
            trackings = PaymentTracking.objects.filter(subscription=None)
            
            for tracking in trackings:
                try:
                    payment = Payment.objects.get(arc_order=tracking.arc_order)
                except Exception as e:
                    payment = ''
                    pass

                if payment:
                    tracking.arc_user = payment.subscription.arc_user
                    tracking.subscription = payment.subscription
                    tracking.payment = payment
                    tracking.partner = payment.subscription.partner
                    tracking.save()
                    # print(payment.subscription.arc_id)

        if options.get('subscription_id') and options.get('uuid') and options.get('arc_order'):
            try:
                arc_user = ArcUser.objects.get(uuid=options.get('uuid'))
                subscription = Subscription.objects.get(arc_id=options.get('subscription_id'))
                payment = Payment.objects.get(arc_order=options.get('arc_order'))

                PaymentTracking.objects.filter(arc_order=options.get('arc_order')).update(
                    arc_user=arc_user,
                    subscription=subscription,
                    payment=payment,
                    partner=subscription.partner
                )
            except Exception as e:
                print(e)

        return 'Ejecucion exitorsa'
