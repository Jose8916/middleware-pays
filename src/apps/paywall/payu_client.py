import base64

from django.conf import settings

import requests


class PayuClient(object):
    """ Api PayU """
    payu_config = settings.PAYU_CONFIG

    def createToken(self, profile, card):
        response_end = {'status': False}
        try:
            params = {
                "language": self.payu_config['language'],
                "command": "CREATE_TOKEN",
                "merchant": {
                    "apiLogin": self.payu_config['apiLogin'],
                    "apiKey": self.payu_config['apiKey'],
                },
                "creditCardToken": {
                    "payerId": str(profile['id']),
                    "name": profile['name_complete'],
                    "identificationNumber": profile['doc_number'],
                    "paymentMethod": card['method'],
                    "number": card['number'],
                    "expirationDate": str(card['year']) + '/' + str(card['month'])
                }
            }
            url = self.payu_config['url_base'] + self.payu_config['url_payment']
            headers = self.getHeaders()
            response = requests.post(url, json=params, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                if response_data['code'] == 'SUCCESS':
                    response_end = {
                        'status': True,
                        'data': response_data
                    }
                else:
                    response_end = {
                        'status': False,
                        'message': 'Error en la integración con PayU',
                        'data': response_data
                    }

        except Exception as e:
            import traceback
            print("type error: " + str(e))
            print(traceback.format_exc())
            response_end = {
                'status': False,
                'message': {'error': str(e), 'trace': traceback.format_exc()}
            }

        return response_end

    def getHeaders(self):
        headers = {
            'content-type': 'application/json',
            'Accept-Charset': 'UTF-8',
            'Accept': 'application/json',
            'accept-language': 'es',
            'Content-Length': 'length',
            'Authorization': 'Basic {0}'
        }

        token = self.payu_config['apiLogin'] + ':' + self.payu_config['apiKey']
        token = token.encode("utf-8")
        authorization = base64.b64encode(token)
        headers['Authorization'] = headers['Authorization'].format(authorization)
        return headers
