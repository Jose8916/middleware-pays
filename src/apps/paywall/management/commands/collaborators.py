import json
import requests

from sentry_sdk import capture_exception, capture_event
from django.core.management.base import BaseCommand
from apps.paywall.models import Subscription, Collaborators


class Command(BaseCommand):
    help = 'Este comando enlaza los deliveys'
    """
        python3 manage.py collaborators
    """

    def handle(self, *args, **options):
        collaborators = Collaborators.objects.filter(subscription=None)
        for collaborator in collaborators:
            if collaborator.data:
                try:
                    subscription_id = collaborator.data['subscriptionID']
                except:
                    pass
                if subscription_id:
                    try:
                        subscription = Subscription.objects.get(arc_id=int(subscription_id))
                    except:
                        subscription = None

                    if subscription:
                        print(subscription)
                        collaborator.subscription = subscription
                        collaborator.save()
