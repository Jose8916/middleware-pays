from django.core.management.base import BaseCommand
from apps.paywall.models import Payment, Operation, PaymentProfile, Subscription, PaymentTracking
from apps.siebel.models import LoadProfile
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'actualiza  a los usuarios que compraron por PWA sin datos de pago'
    # python3 manage.py update_profile_to_subscriptions.py

    def add_arguments(self, parser):
        parser.add_argument('--load', nargs='?', type=str)

    def handle(self, *args, **options):
        lista = []
        if options.get('load'):
            profiles = LoadProfile.objects.all()
            for profile in profiles:
                lista.append({
                    "id_profile": profile.id_profile,
                    "arc_id": profile.arc_id
                })
        else:
            lista = [
                {
                    "id_profile": 17898,
                    "arc_id": 4621111896063439
                }
            ]

        for lis in lista:
            profile = PaymentProfile.objects.get(id=lis.get('id_profile'))
            try:
                subscription = Subscription.objects.get(
                    arc_id=lis.get('arc_id')
                )
                if subscription:
                    subscription.payment_profile = profile
                    subscription.save()
            except Exception as e:
                print(e)
                pass

            try:
                payments = Payment.objects.filter(
                    subscription__arc_id=lis.get('arc_id')
                )
                for payment in payments:
                    payment.payment_profile = profile
                    payment.save()
            except Exception as e:
                print(e)
                pass

            try:
                operations = Operation.objects.filter(
                    payment__subscription__arc_id=lis.get('arc_id')
                )
                for operation in operations:
                    operation.payment_profile = profile
                    operation.save()
            except Exception as e:
                print(e)
                pass
        print('completado')
        print(lista)
