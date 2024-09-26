from django.core.management.base import BaseCommand

from apps.paywall.models import Subscription, UserOffer, HashCollegeStudent
from apps.pagoefectivo.models import CIP


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    # update_offers --subscripcion_pag_efect 1

    def add_arguments(self, parser):
        parser.add_argument('--all', nargs='?', type=str)
        parser.add_argument('--subscripcion_pag_efect', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('all'):
            for subscription in Subscription.objects.all():
                subscription.save()
                subscription.register_offer()

            for user_offer in UserOffer.objects.all():
                user_offer.save()

        if options.get('subscripcion_pag_efect'):
            cips = CIP.objects.filter(subscription__isnull=False)
            for cip in cips:
                user_offer = None

                try:
                    user_offer = UserOffer.objects.get(
                        arc_user=cip.arc_user,
                        campaign=cip.subscription.campaign,
                        subscription=None
                    )
                except UserOffer.MultipleObjectsReturned:
                    print('multiples suscripciones')
                    user_offer = UserOffer.objects.filter(
                        arc_user=cip.arc_user,
                        campaign=cip.subscription.campaign,
                        subscription=None
                    ).last()
                except Exception as e:
                    print(e)

                if user_offer:
                    if not user_offer.subscription:
                        print(cip.subscription)
                        user_offer.subscription = cip.subscription
                        user_offer.save()

        if options.get('university'):
            user_offers = UserOffer.objects.filter(
                offer=UserOffer.OFFER_UNIVERSITY
            ).exclude(subscription=None)

            for user_offer in user_offers:
                university = None
                if CIP.objects.filter(subscription=user_offer.subscription).exists():
                    try:
                        university = HashCollegeStudent.objects.get(
                            arc_user=user_offer.arc_user,
                            site=subscription.partner,
                            user_offer=None
                        )
                    except HashCollegeStudent.MultipleObjectsReturned:
                        print('multiples suscripciones')
                        university = HashCollegeStudent.objects.filter(
                            arc_user=user_offer.arc_user,
                            site=subscription.partner,
                            user_offer=None
                        ).last()
                    except Exception as e:
                        print(e)

                    if university:
                        if not university.subscription:
                            print(user_offer.subscription)
                            university.user_offer = user_offer
                            university.save()
