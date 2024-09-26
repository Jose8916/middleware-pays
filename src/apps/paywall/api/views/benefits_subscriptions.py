from datetime import datetime
from sentry_sdk import capture_exception

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

import json
import requests

# from ....signwall.utils import get_paywall_account_id
from ...models import SubscriptionBenefit, LogSubscriptionBenefits


class ApiBenefitsSubscriptionsView(APIView):
    permission_classes = (AllowAny,)
    origin = 'PAYWALL'

    def get(self, request, id):
        state = status.HTTP_400_BAD_REQUEST

        # Verify session in e suite
        # paywall_account_id = get_paywall_account_id(request)
        paywall_account_id = True

        if paywall_account_id:
            try:
                SubscriptionBenefitsAll = SubscriptionBenefit.objects.filter(subscription_id=id, state=True, state_cancelled=False)

                for SubscriptionBenefitsItem in SubscriptionBenefitsAll:

                    benefit = SubscriptionBenefitsItem.benefit

                    if benefit.be_code == 'peruquiosco':
                        # config
                        url = str(benefit.be_config['url']) + 'anular'
                        header = benefit.be_config['header']

                        params = {
                            'suscripcionid': SubscriptionBenefitsItem.subscription.id,
                            'operacionid': '',
                            'origin': self.origin
                        }

                        response = requests.get(url, headers=header, params=params)
                        logReponse = {}
                        if response.status_code == 200:
                            response = response.json()

                            if int(response['status']) == 1:
                                SubscriptionBenefitsItem.state_cancelled = True
                                SubscriptionBenefitsItem.date_cancelled = datetime.now()
                                SubscriptionBenefitsItem.save()

                            logReponse = response

                        LogSubscriptionBenefits.objects.create(
                            log_benefit=benefit.be_code,
                            log_type='CANCELLED',
                            log_request=json.dumps(params),
                            log_response=json.dumps(logReponse),
                            subsbenefit_id=SubscriptionBenefitsItem.id
                        )

                    elif benefit.be_code == 'club':
                        # config
                        url = str(benefit.be_config['url']) + 'annulled'
                        header = benefit.be_config['header']

                        params = {
                            'key': header['KEY'],
                            'ope_id': SubscriptionBenefitsItem.subscription.id,
                            'origin': self.origin
                        }

                        response = requests.get(url, headers={}, params=params)
                        logReponse = {}
                        if response.status_code == 200:
                            SubscriptionBenefitsItem.state_cancelled = True
                            SubscriptionBenefitsItem.date_cancelled = datetime.now()
                            SubscriptionBenefitsItem.save()

                        LogSubscriptionBenefits.objects.create(
                            log_benefit=benefit.be_code,
                            log_type='CANCELLED',
                            log_request=json.dumps(params),
                            log_response=json.dumps(logReponse),
                            subsbenefit_id=SubscriptionBenefitsItem.id
                        )
                        response = {'La Suscripción ' + str(id) + ' fue anulado correctamente.'}

                    state = status.HTTP_200_OK

            except Exception as e:
                import traceback
                capture_exception()
                print("type error: " + str(e))
                print(traceback.format_exc())

                pass
                response = {'No se encontró la suscripción es estado para anular.'}

            print('ID: ' + str(id))

        else:
            response = {'Es necesario que el usuario se encuentre con sesión.'}
            state = status.HTTP_401_UNAUTHORIZED

        return Response(response, status=state)
