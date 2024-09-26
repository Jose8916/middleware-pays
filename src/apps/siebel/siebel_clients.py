from urllib.parse import urljoin

from django.conf import settings
from sentry_sdk import capture_exception, add_breadcrumb, capture_event
import requests
import csv
import io
import time


class ClientBase(object):

    def api_request(self, url, method, *arg, **kwarks):
        try:
            response = getattr(requests, method)(url, *arg, **kwarks)
            data = response.json()
        except Exception as e:
            print(e)
            capture_exception()
        else:
            if response.status_code == 200:
                return data
            else:
                return {"error": response.status_code}


class SiebelClient(ClientBase):

    def unsubscribe(self, cod_delivery, date_low, test_mode):
        headers = {}
        path = 'wsSuscripcionesPaywall/anular.suscripciones?codDelivery={cod_delivery}&fchAnulacion={date_unsubscribe}'\
            .format(
                cod_delivery=cod_delivery,
                date_unsubscribe=date_low.strftime("%d/%m/%Y")
            )

        url = '{domain}/{path}'.format(
            domain=settings.PAYWALL_SIEBEL_IP,
            path=path
        )
        if test_mode:
            print(url)
            return None, None
        else:
            try:
                response = requests.request("GET", url, data="", headers=headers)
                result = response.json()

            except Exception:
                capture_exception()

            else:
                if response.status_code == 200:
                    return path, result
                else:
                    return path, str(response.text)

            # return self.api_request(url=url, headers=headers, json={}, method='get')
