from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.paywall.models import UserOffer, Subscription


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        user_offer = UserOffer.objects.filter(
            arc_campaign='elcomercio-free',
        ).filter(subscription__isnull=True)

        for user in user_offer:
            subscriptions = Subscription.objects.filter(
                arc_user__uuid=user.arc_user.uuid,
                plan__arc_pricecode=settings.SUBSCRIPTION_7_DAYS_PRICECODE
            )
            for subscription in subscriptions:
                query = UserOffer.objects.filter(
                    arc_user__uuid=user.arc_user.uuid
                ).filter(
                    Q(arc_campaign='elcomercio-free') | Q(campaign__name='elcomercio-free'),
                )
                print('------------------')
                print(user.arc_user.uuid)
                print(subscription.arc_id)
                print('------------------')
                query.update(
                    subscription=subscription
                )
        return 'registros'
