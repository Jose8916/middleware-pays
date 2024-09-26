from urllib.parse import quote, urlencode
import base64
import hashlib
import hmac
import json
import time
import uuid
import requests
from django.http import HttpResponse
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paywall.api.serializers.facebook_pixel import FacebookPixelSerializer
from apps.paywall.classes.history_state import HistoryState
from apps.paywall.models import Subscription


class FacebookPixelGenerator(object):
    """
        https://developers.facebook.com/docs/instant-articles/subscriptions/account-linking
    """

    def generate_signed_fb_event_tag(self, event_name, event_data):
        pixel_id = '192820708803212'  # settings.PIXEL_ID
        app_secret = '%{AQICAHjsOjPySKOyNi6fCzRsZWdpVLIgdyIpEuNiwK3RkBLYDQEA38dJMtWQXEwHzTPcwCuMAAAAfjB8BgkqhkiG9w0BBwagbzBtAgEAMGgGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMepXzE2IgVjsJ1a3EAgEQgDsxI6hoEVKbAKeibj/gH5SS0yz/x61vhZA9QB/yLeJYrwK/DWZnoplNhtVplQrFBqOM5igwxLvxBLZ58g==}'  # settings.APP_SECRET
        payload = {
            'id': pixel_id,
            'ev': event_name,
            'cd': event_data,
            'noscript': 1,
        }
        return self.build_browser_tag(payload, app_secret)

    def get_random_uuid(self):
        # return random hex Representation id using MAC address and time component
        id = uuid.uuid1()
        return id.hex

    def hash_hmac(self, encryption_method, data, key):
        # res = hmac.new(key.encode(), data.encode(), encryption_method).hexdigest()
        # return res
        data = data.encode("utf-8")
        digest = hmac.new(key.encode("utf-8"), data, digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode()

    def encode_to_query_string(self, params):
        encoded_params = []
        for key, value in params.items():
            if not type(value) is dict:
                value = quote(str(value))
                encoded_params.append("{key}={value}".format(key=key, value=value))
            else:
                inner_params = []

                for inner_key, inner_value in value.items():
                    if type(inner_value) is str:
                        value_to_set = inner_value
                    else:
                        value_to_set = json.dumps(inner_value)
                    value_to_set = quote(value_to_set, safe="")
                    key_to_set = quote("[" + inner_key + "]")
                    inner_params.append("{key}{key_to_set}={value_to_set}".format(
                        key=key,
                        key_to_set=key_to_set,
                        value_to_set=value_to_set)
                    )
                encoded_params.append('&'.join(inner_params))
        return '&'.join(encoded_params)

    def build_browser_tag(self, params, secret, base_url='https://www.facebook.com/tr'):
        params['eid'] = self.get_random_uuid()
        params['ts'] = int(time.time()) * 1000
        query_str = self.encode_to_query_string(params)
        query_str2 = urlencode(params)
        print(query_str)
        print(query_str2)

        signature = quote(self.hash_hmac('sha256', query_str, secret), safe="")
        uri = base_url + '?' + query_str + '&sig=' + signature
        return '<img src="{uri}" style="display: none;" />'.format(uri= uri)


class FacebookPixelView(APIView):
    """
        https://developers.facebook.com/docs/instant-articles/subscriptions/account-linking
    """

    permission_classes = (AllowAny, )
    renderer_classes = [TemplateHTMLRenderer]

    def get(self, request, *args, **kwargs):
        """ """
        print('post')
        facebook_pixel = request.data.get('facebook_pixel')
        if not facebook_pixel:
            facebook_pixel = {
                "event_name": "Subscribe",
                "subscription_value": 29.00,
                "currency": "PEN",
                "subscription_id": "c391a4ec-d118-420f-83b0-0b023f22a2da"
            }

        serializer = FacebookPixelSerializer(data=facebook_pixel)

        if serializer.is_valid(raise_exception=True):
            pixel_data = serializer.data
            event_data = {
                'subscription_id': pixel_data['subscription_id'],
            }
            if 'is_subscriber' in pixel_data:
                event_data['is_subscriber'] = pixel_data['is_subscriber']

            if 'currency' in pixel_data:
                event_data['currency'] = pixel_data['currency']

            if 'subscription_value' in pixel_data:
                event_data['value'] = pixel_data['subscription_value']

            pixel = FacebookPixelGenerator().generate_signed_fb_event_tag(
                event_name=pixel_data['event_name'],
                event_data=event_data
            )

            data = {'pixel': pixel}

            datap = {
                'v': '1',  # API Version.
                'tid': 'UA-70251304-38',  # Tracking ID / Property ID.
                # Anonymous Client Identifier. Ideally, this should be a UUID that
                # is associated with particular user, device, or browser instance.
                'cid': '555',
                't': 'event',  # Event hit type.
                'ec': 'category55',  # Event category.
                'ea': 'action55',  # Event action.
                'el': 'label55',  # Event label.
                'ev': 'value55',  # Event value, must be an integer
            }

            response = requests.post(
                'http://www.google-analytics.com/collect', data=datap)

            # If the request fails, this will raise a RequestException. Depending
            # on your application's needs, this may be a non-error and can be caught
            # by the caller.
            response.raise_for_status()
            return HttpResponse(response.text)
            #return Response(data, template_name='pixel.html')
