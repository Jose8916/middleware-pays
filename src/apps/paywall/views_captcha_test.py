import requests

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.views.generic import TemplateView
from ..paywall.forms import FormWithCaptcha


class CaptchaView(TemplateView):
    template_name = 'captcha_test.html'

    def post(self, request):
        ''' Begin reCAPTCHA validation '''
        # form = FormWithCaptcha(request.POST)
        # if form.is_valid():
        #     return HttpResponse("siiii.")
        # else:
        #     return HttpResponse("noooo.")
        recaptcha_response = request.POST.get('g-recaptcha-response')
        return HttpResponse(recaptcha_response)
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = r.json()
        ''' End reCAPTCHA validation '''

        hola = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'public': settings.RECAPTCHA_PUBLIC_KEY
        }

        if result['success']:
            return HttpResponse("exito.")
        else:
            return HttpResponse(settings.RECAPTCHA_PUBLIC_KEY)
