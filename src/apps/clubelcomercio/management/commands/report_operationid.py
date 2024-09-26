from django.core.management.base import BaseCommand

from apps.clubelcomercio.models import ClubSubscription
from apps.paywall.models import Subscription
from apps.piano.models import SubscriptionMatchArcPiano
import csv


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def add_arguments(self, parser):
        parser.add_argument('--all', nargs='?', type=str)

    def handle(self, *args, **options):
        if options.get('all'):
            with open('/tmp/club_operations.csv', 'a') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(
                    [
                        'subscription_id',
                        'operation_id'
                    ]
                )
                sub_list = Subscription.objects.filter(delivery__isnull=False)
                for sub_obj in sub_list.iterator():
                    club = ClubSubscription.objects.filter(
                        subscription__arc_id=sub_obj.arc_id
                    ).order_by('created').last()
                    if club:
                        writer.writerow(
                            [
                                sub_obj.arc_id,
                                club.club_operation
                            ]
                        )
            csvFile.close()
        else:
            with open('/tmp/club_operations1.csv', 'a') as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow(
                    [
                        'subscription_id_arc',
                        'subscription_id_piano',
                        'operation_id',
                        'brand'
                    ]
                )
                list_subscription = SubscriptionMatchArcPiano.objects.all()

                for subs in list_subscription.iterator():
                    try:
                        club_integration = ClubSubscription.objects.filter(
                            subscription__arc_id=subs.subscription_id_arc
                        ).order_by('created').last()
                        # print(str(subs) + " '" + str(club_integration.club_operation))
                        writer.writerow(
                            [
                                subs.subscription_id_arc,
                                subs.subscription_id_piano,
                                club_integration.club_operation,
                                subs.brand
                            ]
                        )
                    except:
                        print('error' + ' ' + str(subs))
            csvFile.close()
            print('Termino la ejecucion')
