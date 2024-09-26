from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from sentry_sdk import capture_event, capture_exception, capture_message
import requests

from ...models import SubscriberPrinted, UserOffer, OfferToken, Campaign, BundlePlan, OfferBase


CAMPAIGN_CACHE_MAX_AGE = 900


class ApiSubscriberValidationView(APIView):
    permission_classes = (AllowAny, )

    def get(self, request, site):
        """
        Retorna la campaña en curso.

        Parámetros:
        - doctype: Tipo de documento.
        - docnumber: Número de documento.
        - token: /api/subscription-online/token/
        """

        error = None
        result = {}
        info = {}
        document_type = request.query_params.get('doctype')
        document_number = request.query_params.get('docnumber')
        token = request.query_params.get('token')
        event = request.query_params.get('event')
        subscriptor_event = request.query_params.get('subscriptor_event', '')
        from_fia = request.query_params.get('from_fia')
        cache_max_age = CAMPAIGN_CACHE_MAX_AGE

        campaign = None
        if from_fia:
            campaign = Campaign.objects.get_facebook_by_site(site=site)

            if not campaign:
                error = 'No existe plan Facebook'

        elif event and not subscriptor_event:
            # Retorna la campaña del evento requerido "param:event"
            campaign = Campaign.objects.get_by_event(site=site, event=event)

            if campaign:
                result['event'] = campaign.event
                # Validation available
                #if not campaign.is_enabled():
                #    campaign = None
                #    error = 'El evento {} ha terminado.'.format(event.upper())

            else:
                error = 'No existe el evento'

        elif document_type and document_number and document_number != '00000000':
            info = {
                'documentType': document_type,
                'documentNumber': document_number,
            }

            # Valida que sea un usuario de ARC
            offer_token, error = self.get_offer_token(
                token=token,
                document_number=document_number,
                request=request
            )

            if offer_token and not error:
                offer_token.create_token()
                offer_token.save()

                campaign, print_suscriber, error = self.get_campaign_by_document(
                    site=site,
                    document_type=document_type,
                    document_number=document_number,
                    user_uuid=offer_token.user_uuid,
                    event=subscriptor_event
                )
                if campaign and print_suscriber and not error:
                    result['subscriber'] = {
                        'firstName': print_suscriber.us_data['result']['user']['name'],
                        'lastName': print_suscriber.us_data['result']['user']['lastname'],
                        'secondLastName': '',
                        'printed': True,
                        'freeAccess': campaign.offer == Campaign.OFFER_SUBSCRIBER_FULL,
                    }

        elif token:
            user_offer = UserOffer.objects.get_by_token(token=token)

            if user_offer:
                if user_offer.campaign.is_active:
                    """
                    capture_event(
                        {
                            'message': 'universitario oferta',
                            'extra': {
                                'document_type': document_type,
                                'document_number': document_number,
                                'token': token,
                                'user_offer': user_offer,
                            }
                        }
                    )
                    """
                    campaign = user_offer.campaign
                else:
                    if user_offer.offer == OfferBase.OFFER_UNIVERSITY:
                        error = 'Código inválido, genere un nuevo código'
                    else:
                        error = 'Campaña inactiva'
            else:
                error = 'Acceso incorrecto'

        if token:
            cache_max_age = 90

        if not campaign:
            if subscriptor_event and event:
                campaign = Campaign.objects.get_by_event(site=site, event=event)
            else:
                campaign = Campaign.objects.get_default_by_site(site=site)

        if info:
            result['info'] = info

        if subscriptor_event:
            result['event'] = campaign.event

        if error:
            result['error'] = error

        result.update(campaign.get_paywall_data())

        response = Response(
            result,
            status=status.HTTP_200_OK
        )
        response['Cache-Control'] = 'max-age={}'.format(cache_max_age)
        return response

    def get_print_suscriber(self, site, document_type, document_number):
        url = '{club_url}/services/subscriber/validate/api_key/' \
            '{token}/api_client/paywall/programa/' \
            '{site}/tipo_documento/' \
            '{document_type}/numero_documento/{document_number}'.format(
                club_url=settings.PAYWALL_CLUB_URL,
                token=settings.PAYWALL_CLUB_TOKEN_SUBSCRIPTOR,
                site=site,
                document_type=document_type,
                document_number=document_number,
            )

        try:
            response = requests.get(url)
            data = response.json()

        except Exception:
            capture_exception()

        else:
            if data.get('status'):
                try:
                    instance = SubscriberPrinted.objects.get(
                        us_doctype=document_type,
                        us_docnumber=document_number,
                    )

                except SubscriberPrinted.DoesNotExist:
                    instance = SubscriberPrinted(
                        us_doctype=document_type,
                        us_docnumber=document_number,
                    )

                instance.us_name = data['result']['user']['name']
                instance.us_lastname = data['result']['user']['lastname']
                instance.us_data = data
                instance.save()

                return instance

    def get_offer_token(self, token, document_number, request):
        error = None
        offer_token = None

        if not token:
            return offer_token, error

        try:
            offer_token = OfferToken.objects.get(token=token)

        except OfferToken.DoesNotExist:
            error = 'Ocurrió un error, intente nuevamente.'

            # Se obvia el token que se usa para monitoreo de caídas
            if token != 'lUE0Cy9H098QHWPY4nu6udR6BLSg2IUwJp1k98R2bwyl8791T2':
                capture_event(
                    {
                        'message': 'No se encontró OfferToken',
                        'extra': {
                            'query_params': request.query_params,
                        }
                    }
                )

        else:
            # Valida que no exceda el número de intentos
            if document_number and document_number not in offer_token.dni_list:
                offer_token.dni_list.append(document_number)

                if len(offer_token.dni_list) > 3:

                    # Guarda veinte primeros intentos
                    if len(offer_token.dni_list) < 20:
                        offer_token.save()

                    error = 'Superó el número de intentos permitidos.'
                    offer_token = None

                else:
                    offer_token.save()

        return offer_token, error

    def get_campaign_by_document(self, site, document_type, document_number, user_uuid, event):
        """
            Retorna la campaña según el documento y site ingresado.
        """
        campaign = None
        error = None

        print_suscriber = self.get_print_suscriber(
            site=site,
            document_type=document_type,
            document_number=document_number
        )

        if not print_suscriber:
            error = 'El número de documento {} no cuenta con una suscripción impresa.'.format(document_number)
            return campaign, print_suscriber, error

        if site == 'elcomercio':
            free_campaign = Campaign.objects.get_free_by_site(site=site)

            if free_campaign:
                if not free_campaign.siebel_codes:
                    capture_message('La campaña gratuita ID %s no tiene codigos siebel.' % free_campaign.id)

                # Si tiene una suscripción de 7 días de El Comercio retornar campaña gratuita.
                for code in print_suscriber.get_siebel_codes():
                    if code in free_campaign.siebel_codes:
                        campaign = free_campaign
                        break

        if not campaign:
            if event:
                campaign = Campaign.objects.get_offer_event_by_site(site=site, event=event)
            else:
                campaign = Campaign.objects.get_offer_by_site(site=site)

        # Valida que el DNI no tenga la suscripción comprada
        if UserOffer.objects.filter(
            dni=document_number,
            site=site,
            subscription__isnull=False,
        ).exists():
            error = 'El número de documento {} ya accedió al descuento.'.format(document_number)
            campaign = None
            return campaign, print_suscriber, error

        # Valida que el usuario no tenga ofertas con otros DNI
        if UserOffer.objects.filter(
            user_uuid=user_uuid,
        ).exclude(
            dni=document_number,
        ).exists():
            error = 'Ya accedió con un número de documento distinto a {}.'.format(document_number)
            campaign = None
            return campaign, print_suscriber, error

        user_offer, created = UserOffer.objects.get_or_create(
            user_uuid=user_uuid,
            campaign=campaign,
            defaults={
                'dni': document_number,
            }
        )

        if user_offer.subscription_id:
            error = 'Ya accedió a una oferta.'
            campaign = None

        elif campaign.offer == Campaign.OFFER_SUBSCRIBER_FULL:
            campaign.link_user(user_uuid)

        return campaign, print_suscriber, error


class BundleCampaignView(APIView):
    permission_classes = (AllowAny, )

    def get(self, request, site):
        """
        Retorna la campaña bunddle en curso.
        """

        result = self.get_bundle_campaigns(site=site)

        response = Response(
            result,
            status=status.HTTP_200_OK
        )
        response['Cache-Control'] = 'max-age={}'.format(CAMPAIGN_CACHE_MAX_AGE)
        return response

    def get_digital_campaigns(self, site):
        campaign = Campaign.objects.get_default_by_site(site=site)

        return [campaign.get_display_data(), ]

    def get_bundle_campaigns(self, site):

        bundle_plans = BundlePlan.objects.filter(
            is_active=True,
            partner__partner_code=site,
        )

        result = []
        for bundle_plan in bundle_plans:
            result.append(bundle_plan.get_display_data())

        return result

    def get_benefits_cover_page(self, site):

        benefits_cover_page = BenefitsCoverPage.objects.filter(
            state=True,
            partner__partner_code=site,
        )

        result = []
        for benefit_cover_page in benefits_cover_page:
            result.append(benefit_cover_page.get_display_data())

        return result
