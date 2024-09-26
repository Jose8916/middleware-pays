from django.conf.urls import url

from .views.payment_notification import ApiPaymentNotificationView
from .views.payment_recurrence import ApiPaymentRecurrenceView
from .views.subscription_cancel import ApiSubscriptionCancelView
from .views.subscriptin_fail_renew import ApiSubscriptionFailRenewView
from .views.payment_update_method import ApiUpdatePaymentMethodView
from .views.payment_notification_siebel import NotificationPaymentSiebelView
from .views.user_update import UserUpdateView


urlpatterns = [
    # SERVERLESS APIs
    url(
        r'^subscription/start/$',
        ApiPaymentNotificationView.as_view(),
        name='subscription_start'
    ),
    url(
        r'^subscription/renew/$',
        ApiPaymentRecurrenceView.as_view(),
        name='subscription_renew'
    ),
    url(
        r'^subscription/cancel/$',
        ApiSubscriptionCancelView.as_view(),
        name='subscription_cancel'
    ),
    url(
        r'^subscription/fail_renew/$',
        ApiSubscriptionFailRenewView.as_view(),
        name='subscription_fail_renew'
    ),
    url(
        r'^subscription/update_payment_method/$',
        ApiUpdatePaymentMethodView.as_view(),
        name='update_payment_method'
    ),
    url(
        r'^user/update/$',
        UserUpdateView.as_view(),
        name='user_update'
    ),
    url(
        r'^payment/status/$',
        NotificationPaymentSiebelView.as_view(),
        name='payment_status'
    ),
]
