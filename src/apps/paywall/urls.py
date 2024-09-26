from django.conf.urls import url

from .views import PaywallCollaboratorsView, PaywallCollaboratorsAnnulledView, FacebookPixelView
from .report_views import SalesReportView, SubscriptionRepeatedReport, LongPeridTimeSubscriptions
from .views_template.repeated_subscriptions import SubscriptionDoubleReport
from .views_template.type_of_low import TypeOfLowView
from .views_template.high_low_subscriptions import HightLowSubscriptions
from .views_template.low_subscriptions_by_suspension import LowSubscriptionsBySuspension
from .views_template.low_subscriptions_by_suspension_type import LowSubscriptionsBySuspensionType
from .report_by_plan_views import SalesByPlanReportView
from .views_template.report_by_plan import AllSalesByPlanReportView
from .views_template.medium_high_subscriptions import HighSubscriptionsByMediumReportView
from .renewal_failures import RenewalReportView
from apps.paywall.report.subscription_state import SuscriptionStateReportView  # este reemplazaria a RenewalReportView
from .views_captcha_test import CaptchaView
from .tests import TestRenewView
from apps.paywall.suspended_payment import NoPaymentJanuaryReportView, PaymentNotChargedReportView
from apps.paywall.not_payment import NoPaymentReportView
from apps.paywall.report_payu_by_plan import SalesByPlanPayuReportView

urlpatterns = [
    # Test
    url(
        r'^test_renew/',
        TestRenewView.as_view(),
        name='test_renew'
    ),
    url(
        r'^facebook-pixel/',
        FacebookPixelView.as_view(),
        name='admin-paywall-collaborators-list'
    ),

    # Admin
    url(
        r'^collaborators-list/$',
        PaywallCollaboratorsView.as_view(),
        name='admin-paywall-collaborators-list'
    ),
    url(
        r'^collaborators-upload/$',
        PaywallCollaboratorsView.as_view(),
        name='admin-paywall-collaborators-upload'
    ),
    url(
        r'^collaborators-annulled/$',
        PaywallCollaboratorsAnnulledView.as_view(),
        name='admin-paywall-collaborators-annulled'
    ),
    url(
        r'^admin/sales/report/$',
        SalesReportView.as_view(),
        name='sales_report'
    ),
    url(
        r'^admin/sales_plan_report/$',
        SalesByPlanReportView.as_view(),
        name='sales_plan_report'
    ),
    url(
        r'^admin/report_sales/$',
        AllSalesByPlanReportView.as_view(),
        name='report_sales'
    ),
    url(
        r'^admin/subscriptions_by_medium/$',
        HighSubscriptionsByMediumReportView.as_view(),
        name='subscriptions_by_medium'
    ),

    url(
        r'^admin/sales_plan_payu_report/$',
        SalesByPlanPayuReportView.as_view(),
        name='sales_plan_payu_report'
    ),
    url(
        r'^admin/no_payment_january/$',
        NoPaymentJanuaryReportView.as_view(),
        name='no_payment_january'
    ),
    url(
        r'^admin/no_payment/$',
        NoPaymentReportView.as_view(),
        name='no_payment'
    ),
    url(
        r'^admin/payment_not_charged/$',
        PaymentNotChargedReportView.as_view(),
        name='payment_not_charged'
    ),
    url(
        r'^admin/user_suscriptions/$',
        SubscriptionRepeatedReport.as_view(),
        name='user_suscriptions'
    ),
    url(
        r'^admin/long_period_time/$',
        LongPeridTimeSubscriptions.as_view(),
        name='long_period_time'
    ),
    url(
        r'^admin/subscription_double/$',
        SubscriptionDoubleReport.as_view(),
        name='subscription_double'
    ),
    url(
        r'^admin/subscription_high_low/$',
        HightLowSubscriptions.as_view(),
        name='subscription_high_low'
    ),
    url(
        r'^admin/low_by_suspension/$',
        LowSubscriptionsBySuspension.as_view(),
        name='low_by_suspension'
    ),
    url(
        r'^admin/low_by_suspension_type/$',
        LowSubscriptionsBySuspensionType.as_view(),
        name='low_by_suspension_type'
    ),
    url(
        r'^admin/collection_attempts/$',
        SuscriptionStateReportView.as_view(),
        name='collection_attempts'
    ),
    url(
        r'^admin/type_of_low/$',
        TypeOfLowView.as_view(),
        name='type_of_low'
    ),
    url(
        r'^captcha/$',
        CaptchaView.as_view(),
        name='captcha'
    ),
]
