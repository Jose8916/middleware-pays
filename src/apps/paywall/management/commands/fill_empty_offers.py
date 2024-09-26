from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.paywall.models import UserOffer, Subscription, OfferToken


class Command(BaseCommand):
    help = 'llena DNIs vacios de las ofertas de los planes suscriptores'

    def add_arguments(self, parser):
        parser.add_argument('--sku', nargs='?', type=str)

    def handle(self, *args, **options):
        # if settings.ENVIRONMENT == 'test':
        #     arc_sku = options.get('sku')
        # elif settings.ENVIRONMENT == 'production':
        #     arc_sku = options.get('sku')

        user_offer = UserOffer.objects.filter(
            arc_sku=options.get('sku'),
        ).filter(Q(dni__isnull=True) | Q(dni='')).exclude(subscription__isnull=True)

        for user in user_offer:
            offer_tokens = OfferToken.objects.filter(
                user_uuid=user.arc_user.uuid
            )

            for offer_token in offer_tokens:
                if offer_token.dni_list:
                    if len(offer_token.dni_list) == 1 and offer_token.dni_list[0].isnumeric() and user.subscription:
                        print('------------------')
                        print(user.arc_user.uuid)
                        print(user.dni)
                        print(user.subscription.arc_id)
                        print('------------------')
                        user.dni = offer_token.dni_list[0]
                        user.save()

        return 'exito'
