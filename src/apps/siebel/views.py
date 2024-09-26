from dal import autocomplete
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_event, capture_exception

from .models import Logs
from .models import Via, Urbanizacion
from .serializers import SiebelSerializer
from apps.paywall.models import Subscription


class ViaAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        # if not self.request.user.is_authenticated():
        #     return Via.objects.none()

        qs = Via.objects.all()

        if self.q:
            qs = qs.filter(via_nombre__istartswith=self.q)

        return qs


class UrbanizacionAutocomplete(autocomplete.Select2QuerySetView):

    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        # if not self.request.user.is_authenticated():
        #     return Via.objects.none()

        qs = Urbanizacion.objects.all()

        if self.q:
            qs = qs.filter(urb_nombre__istartswith=self.q)

        return qs


@method_decorator(csrf_exempt, name='dispatch')
class ApiSiebelCancellationsView(View):
    """
        class ApiSiebelCancellationsView(APIView)
    """
    log_type = 'CANCELLATIONS'
    serializer = SiebelSerializer

    def get(self, request):
        # data = request.GET
        state = status.HTTP_200_OK
        response = {}
        # delivery = request.query_params.get('delivery')

        capture_event(
            {
                'message': 'Siebel cancelation GET',
                'extra': {
                    'get': request.GET,
                    'post': request.POST,
                }
            }
        )
        return JsonResponse(
            {'status': 'OK'}
        )

        try:
            LogsGet = Logs.objects.get(delivery=int(delivery), log_type=self.log_type, state=True)
            response = self.serializer(LogsGet)
            response = response.data

        except Exception:
            capture_exception()
            state = status.HTTP_400_BAD_REQUEST
            response = {'message': 'No se encontraron registros.'}

        return Response(response, status=state)

    def post(self, request):
        # data = request.POST
        state = status.HTTP_200_OK
        response = 'Error en el proceso de registro de la anulación.'

        capture_event(
            {
                'message': 'Siebel cancelation POST',
                'extra': {
                    'get': request.GET,
                    'post': request.POST,
                }
            }
        )
        return JsonResponse(
            {'status': 'OK'}
        )

        if data['delivery'] and data['entecode'] and data['date_cancelled']:
            try:
                Logs.objects.get(delivery=data['delivery'], log_type=self.log_type, state=True)
                response = 'El código delivery ya se encuentra anulado.'
                return Response(response, status=status.HTTP_202_ACCEPTED)
            except Logs.DoesNotExist:
                try:
                    Subscription.objects.get(siebel_delivery=data['delivery'])
                    response = 'La anulación se registró correctamente.'
                    Logs.objects.create(
                        delivery=data['delivery'],
                        log_type=self.log_type,
                        log_request=data,
                        log_response={'message': response}
                    )

                except Subscription.DoesNotExist:
                    response = 'El código delivery no se encuentra en la DB.'
                    state = status.HTTP_400_BAD_REQUEST

        else:
            response = 'Los datos delivery/entecode/date_cancelled no pueden estar vacíos.'
            state = status.HTTP_400_BAD_REQUEST

        return Response(response, status=state)
