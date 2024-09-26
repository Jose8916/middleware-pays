from django.core.management.base import BaseCommand

from apps.clubelcomercio.models import  ClubIntegration


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        club_integrations = ClubIntegration.objects.exclude(
            status_ok=True
        )
        for club_integration in club_integrations.iterator():
            print(club_integration.id)
            club_integration.apply()
