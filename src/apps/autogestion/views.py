from urllib.parse import urljoin

from django.http import JsonResponse, HttpResponse
from django.views.generic import View
import requests

from .models import SiebelSubscription
from apps.paywall.models import Subscription
from apps.arcsubs.utils import timestamp_to_datetime


SIEBEl_COMISIONES_URL = 'http://200.4.199.84'


class ApiBase(View):

    def get_token_header(self, request):
        return token

    def token_is_valid(self, token):
        return token == '109998623fcffa2086f406f8880b24942532d80fc5da0420047ab1ee22f6bdfa'


class SubsctiptionPrintListView(ApiBase):

    def get(self, request):
        document_type = request.GET.get("document_type").upper()
        document_number = request.GET.get("document_number")
        portal = request.GET.get("portal", '').lower()

        if portal not in ['gestion', 'elcomercio']:
            return HttpResponse('No existe el portal', status=404)

        if not document_type or not document_number:
            return HttpResponse('Invalid input', status=405)

        data = {}

        subscriptor = self.get_subscriptor(
            document_type,
            document_number
        )

        data['suscriptor'] = subscriptor

        if subscriptor:
            subscriptor_id = subscriptor['us_codigo']

            subscriptions = self.get_subscriptions(subscriptor_id) or []
            # data['subscriptions'] = [s for s in subscriptions if portal in s['paquete'].replace('ó', 'o').lower()]

            data['subscriptions'] = []
            for subscription in subscriptions:
                data['subscriptions'].append(
                    {
                        'id': subscription['codigo_delivery'],
                        'portal': portal,
                        'category': 'print',
                    }
                )

            for subscription in data['subscriptions']:
                delivery = subscription['id']
                siebel_subscription, _ = SiebelSubscription.objects.get_or_create(
                    delivery=delivery
                )
                siebel_subscription.subscriber_data = subscriptor
                siebel_subscription.data = subscription
                siebel_subscription.save()

        return JsonResponse(data['subscriptions'], safe=False)

    def get_subscriptor(self, document_type, document_number):
        url = urljoin(
            SIEBEl_COMISIONES_URL,
            '/wsPeruQuioscoImpresos/adminpq.consulta'
        )
        payload = {
            'tipdoc': document_type,
            'numdoc': document_number,
        }

        response = requests.get(
            url,
            params=payload
        )
        result = response.json()

        subscriptor = None
        if 'response' in result:
            subscriptor = result['response'].get('suscriptor')

        return subscriptor

    def get_subscriptions(self, subscriptor_id):
        url = urljoin(
            SIEBEl_COMISIONES_URL,
            '/wsClubSuscriptorProducto/consultar.producto'
        )
        payload = {
            'codigo_suscriptor': subscriptor_id
        }

        try:
            response = requests.get(
                url,
                params=payload,
                timeout=30
            )
            result = response.json()
        except:
            subscriptions = []

        else:
            subscriptions = []
            if 'productos' in result:
                subscriptions = result['productos']

        return subscriptions


class SubsctiptionPrintDetailView(ApiBase):

    def get(self, request, subscription_id):
        try:
            siebel_subscription = SiebelSubscription.objects.get(
                delivery=subscription_id
            )
        except SiebelSubscription.DoesNotExists:
            return HttpResponse('No existe', status=404)
        else:
            data = {
                "id": subscription_id,
                "category": "print",
                "name": siebel_subscription.data['paquete'],
                "email": None,
                "periodicity": "mensual",
                "price": 10,
                "deliveryDays": [
                    "lunes",
                    "martes",
                    "miercoles",
                ],
                "lastPaymentDate": siebel_subscription.data['fch_inicio_vigencia'],
                "lastPaymentAmount": 10,
                "nextPaymentDate": siebel_subscription.data['fch_final_vigencia'],
                "nextPaymentAmount": 10
            }

        return JsonResponse(data)


class SubsctiptionDigitalListView(ApiBase):

    def get(self, request):
        document_type = request.GET.get("document_type").upper()
        document_number = request.GET.get("document_number")
        portal = request.GET.get("portal", '').lower()

        if portal not in ['gestion', 'elcomercio']:
            return HttpResponse('No existe el portal', status=404)

        if not document_type or not document_number:
            return HttpResponse('Invalid input', status=405)

        data = {}

        subscriptions = self.get_subscriptions(
            document_type,
            document_number,
            portal
        )

        subscriptions_data = []
        for subscription in subscriptions:
            subscriptions_data.append(
                {
                    'id': subscription.arc_id,
                    'portal': portal,
                    'category': 'digital',
                }
            )

        return JsonResponse({'subscriptions': subscriptions_data}, safe=False)

    def get_subscriptions(self, document_type, document_number, portal):
        return Subscription.objects.filter(
            payment_profile__prof_doc_type=document_type,
            payment_profile__prof_doc_num=document_number,
            partner__partner_code=portal
        )


class SubsctiptionDigitalDetailView(ApiBase):
    def get(self, request, subscription_id):
        try:
            subscription = Subscription.objects.get(
                arc_id=subscription_id
            )
        except Subscription.DoesNotExists:
            return HttpResponse('No existe', status=404)
        else:
            data = {
                "id": subscription_id,
                "category": "digital",
                "name": subscription.data['productName'],
                "email": None,
                "periodicity": "mensual",
                "price": 10,
                "deliveryDays": None,
                "lastPaymentDate": "siebel_subscription.data['fch_inicio_vigencia']",
                "lastPaymentAmount": 10,
                "nextPaymentDate": timestamp_to_datetime(subscription.data['nextEventDateUTC']),
                "nextPaymentAmount": 10
            }

            next_event = subscription.data.get('nextEventDateUTC')
            if next_event:
                data['lastPaymentDate'] = timestamp_to_datetime(next_event)
                data['nextPaymentDate'] = timestamp_to_datetime(next_event)

        return JsonResponse(data)
