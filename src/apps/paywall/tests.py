from django.test import TestCase

from django.http import HttpResponse
from django.template import loader

from apps.paywall.api.views.subscriptin_fail_renew import ApiSubscriptionFailRenewView
from django.views import View

from .models import Operation, Plan, Subscription, Product, Payment


# Create your tests here.
class TestRenewView(View):
    def get(self, request, *args, **kwargs):
        subscription = Subscription.objects.get(
            arc_id=request.GET.get('id_subscription')
        )
        test = ApiSubscriptionFailRenewView()
        test.send_mail_fail_renew_subscription(subscription)

        return HttpResponse('exito')

