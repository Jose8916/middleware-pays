from django.core.management.base import BaseCommand

from apps.paywall.models import  Subscription, Operation


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        subscriptions = Subscription.objects.exclude(state=2)
        count = 0
        count_e = 0
        list_subscriptions = []
        for subscription in subscriptions:
            cantidad = Operation.objects.filter(
                payment__subscription=subscription,
                siebel_delivery__isnull=False).count()
            if not cantidad:
                ope = Operation.objects.filter(
                    payment__subscription=subscription
                ).last()
                try:
                    if ope.ope_amount >= 5:
                        count = count + 1
                        list_subscriptions.append(subscription.arc_id)
                except Exception:
                    pass

            if Operation.objects.filter(
                    payment__subscription=subscription,
                ).exclude(
                    siebel_delivery=None).count():
                count_e = count_e + 1
        print('Suscripciones que no tienen delivery: ' + str(count))
        print('Suscripciones que con delivery: ' + str(count_e))
        print(list_subscriptions)






