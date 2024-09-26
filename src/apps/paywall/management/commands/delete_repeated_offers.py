from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.paywall.models import UserOffer


class Command(BaseCommand):
    help = 'borra ofertas repetidas'

    def add_arguments(self, parser):
        parser.add_argument('--sku', nargs='?', type=str)

    def handle(self, *args, **options):
        list_duplicates = []
        duplicates = UserOffer.objects.values(
            'subscription'
        ).annotate(
            subscription_count=Count('subscription')
        ).filter(
            subscription_count=2,
            arc_sku=options.get('sku')
        )

        for item in duplicates:
            duplicates_dni = UserOffer.objects.values('dni').filter(
                subscription=item['subscription']
            ).annotate(
                dni_count=Count('dni')
            ).filter(dni_count__gt=1)

            if duplicates_dni:
                list_duplicates.append(item['subscription'])

        for item_list in list_duplicates:
            print('------------------')
            print(item_list)
            oferta = UserOffer.objects.filter(subscription=item_list).order_by('created').last()
            print(oferta.subscription.arc_id)
            oferta.delete()
            print('------------------')

        return 'exito'
