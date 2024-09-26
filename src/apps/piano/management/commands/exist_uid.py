# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from sentry_sdk import capture_exception
from apps.piano.piano_clients import VXClient
from apps.paywall.models import Operation, Subscription
from apps.siebel.models import SiebelConfiguration, ReasonExclude, LoadTransactionsIdSiebel, SiebelConfirmationPayment, \
    SubscriptionExclude
from datetime import datetime, timedelta
from django.db.models import Count
from apps.paywall.arc_clients import SalesClient
from django.utils.encoding import smart_str
import csv
from apps.piano.piano_clients import IDClient


class Command(BaseCommand):
    help = 'Ejecuta el comando'

    def handle(self, *args, **options):
        """
            - Servicio que envia los pagos a siebel
            - python3 manage.py list_of_terms --type_term payment --branch sandbox --brand gestion
        """

        list_user = [
            '9a1d2bfa-0ec2-4106-aa8a-eb3bcd784202',
            '66f15ee0-fc91-462e-a254-62c8ca4df50e',
            'cca4e33b-cf97-4668-a3b8-1b3103d52fab',
            'cca4e33b-cf97-4668-a3b8-1b3103d52fab',
            '556d23cc-2e51-410a-b274-6ce9a7d7199c',
            '52e0eadf-bb85-4ff4-b1be-8b7b7ee12540',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            'bf71a97d-68db-42bf-b753-5fe7bd41a918',
            'f38ce3be-a80d-45bc-8fa1-13e4dcbebadc',
            '46a34319-09c6-4d54-81cb-4df1550f1333',
            'bade70e6-c9b0-4c8f-be28-d35776c56c26',
            'd9559897-5770-47dc-9030-8a74dec2bc4d',
            'bade70e6-c9b0-4c8f-be28-d35776c56c26',
            '79376903-42ed-4bb4-9efa-d19d5d88ca35',
            '507b7397-5deb-468a-8a7d-7f8bda1bf6e8',
            '507b7397-5deb-468a-8a7d-7f8bda1bf6e8',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '19bb4c17-28b9-4101-87f8-849f45f1cd6b',
            '49318bb0-d4d0-480e-97fc-5051a6e93288',
            '23f60db7-72f2-4b71-9961-eb33c910fb70',
            '14d2e55e-7b96-4210-86b7-536cfcc75dc8',
            '2edf96b5-b0bc-44f6-9eaf-1d5f58ce8a5c',
            '7dcfd4d4-ad43-4c36-a088-af0544741d0c',
            '1a026b68-5cd7-47fe-9206-bf857ef8688d',
            'e5f86bd8-8ab2-4707-9713-83a30c79fda9',
            '8abfa33e-2d1f-48c4-8d36-607cfc3bc70c',
            '0a21c0ab-7cdf-4971-a645-5bbb90c6a96c',
            '02551b02-da68-4c0c-82b4-cffa88be847c',
            '08289cc2-3ff2-4ce6-8bda-414331084c71',
            '7129b499-5831-48ba-b57d-f70e6ce058df',
            '8c4502e3-4120-4067-b7e5-6657350ce73b',
            '62b78cd0-38fa-47cc-a6f0-732fa0fd6d2f',
            '7f2c61f7-b3dc-47d9-8229-34a5e18a55f1',
            '6364978b-8c89-4985-83ab-6fd47e02a843',
            '2c3c9c0f-7ddd-4fb2-a4ee-9584340bdc3d',
            '4013d127-37c1-49ff-83f1-486ca1175527',
            '863d560c-b720-4a9a-850a-1ec11ea2e96b',
            '6364978b-8c89-4985-83ab-6fd47e02a843',
            '424d3464-de60-49e9-a3b7-54d92370bb07',
            'fb5f6830-3126-4046-8ea2-fc5f23a8f191',
            '104afbec-513c-4f07-8bb6-ebf8357c78bb',
            'a33f44eb-2560-475a-aaeb-b93ce8ed8a39',
            'e795ab6d-f17d-40b9-94c9-a55999d0092d',
            'e795ab6d-f17d-40b9-94c9-a55999d0092d',
            '633df4ff-40fc-4490-bfb8-156645eb387f',
            '28efca55-4125-46cd-8b47-bfd336d9b1bc'
        ]
        list_exist = []
        list_no_exist = []
        for user in list_user:
            data = IDClient().get_uid(user, 'gestion')

            if data.get('user', ''):
                list_exist.append(user)
            else:
                list_no_exist.append(user)
        print(list_exist)
        print(len(list_exist))
        print(list_no_exist)
        print(len(list_no_exist))