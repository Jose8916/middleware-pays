from django.conf.urls import url

from .views.offer_token import OfferTokenAPIView
from .views.subscriber_validation import ApiSubscriberValidationView, BundleCampaignView
from .views.suscripcion_corporativa import SuscripcionCorporativaApiView
from .views.user_subscriptions import UserSubscriptionApiView
from .views.subscriptions_paywall import SubscriptionApiView
from .views.subscriptions_paywall_dwh import SubscriptionUniqueApiView
from .views.terms_and_conditions import TermsAndConditionsApiView
from .views.collaboratos import CollaboratorsApiView
from .views.validate_academic import ValidateUsersAcademicAPIView
from .views.activate_promotion_university import ActivatePromotionAPIView
from .views.universities import UniversitiesApiView
from .views.free_subscriptions import FreeSubscriptionApiView
from .views.high_low import SubscriptionStateView
from .views.user_info_payment import ApiUserInfoPayment
from .views.plans import PlanApiView
from .views.facebook_pixel import FacebookPixelView
from .views.subscriptions_dwh import SubscriptionDwhApiView
from .views.user_with_subscription import UserWithSubscriptionApiView
from .views.log import LogAPIView
from .views.test_command import TestCommandApiView, TestPaymentCommandApiView, TestWebhookPianoApiView

urlpatterns = [
    # PUBLIC APIs
    url(
        r'^subscription-online/token/$',
        OfferTokenAPIView.as_view(),
        name='api_offer_token'
    ),
    url(
        r'^subs-corporativa/$',
        SuscripcionCorporativaApiView.as_view(),
        name='subs_corporativa'
    ),
    url(
        r'^terms-conditions/$',
        TermsAndConditionsApiView.as_view(),
        name='terms_conditions'
    ),
    url(
        r'^log/$',
        LogAPIView.as_view(),
        name='log'
    ),
    # LANDING APIs
    url(
        r'^subscriber/validation/(?P<site>[a-z0-9]+)/$',
        ApiSubscriberValidationView.as_view(),
        name='api_subscriber_validation'
    ),
    url(
        r'^subscriber/validation/(?P<site>[a-z0-9]+)/bundle/$',
        BundleCampaignView.as_view(),
        name='api_bundle_campaign'
    ),
    # API Info User
    url(
        r'^user/payment-profile/(?P<subscription_id>[a-z0-9]+)/$',
        ApiUserInfoPayment.as_view(),
        name='api_user_payment'
    ),

    # API DATAWAREHOUSE
    url(
        r'^user-subscriptions/$',
        SubscriptionApiView.as_view(),
        name='user-subscriptions'
    ),
    url(
        r'^users_subscriptions/$',
        SubscriptionUniqueApiView.as_view(),
        name='users_subscriptions'
    ),
    url(
        r'^subscriptions/$',
        UserSubscriptionApiView.as_view(),
        name='subscriptions'
    ),
    url(
        r'^free-subscriptions/$',
        FreeSubscriptionApiView.as_view(),
        name='free-subscriptions'
    ),
    url(
        r'^plans-paywall/$',
        PlanApiView.as_view(),
        name='plans-paywall'
    ),
    url(
        r'^facebook-pixel/$',
        FacebookPixelView.as_view(),
        name='facebook-pixel'
    ),

    # API DATAWAREHOUSE
    url(
        r'^collaborators/$',
        CollaboratorsApiView.as_view(),
        name='collaborators'
    ),
    url(
        r'^validate_user_academic/$',
        ValidateUsersAcademicAPIView.as_view(),
        name='validate_user_academic'
    ),
    url(
        r'^activate_promotion/$',
        ActivatePromotionAPIView.as_view(),
        name='activate_promotion'
    ),
    url(
        r'^universities/$',
        UniversitiesApiView.as_view(),
        name='universities'
    ),
    url(
        r'^suscriptions_report/$',
        SubscriptionStateView.as_view(),
        name='suscriptions_report'
    ),
    url(
        r'^suscriptions_paywall/$',
        SubscriptionDwhApiView.as_view(),
        name='suscriptions_paywall'
    ),
    url(
        r'^user_with_subscription/$',
        UserWithSubscriptionApiView.as_view(),
        name='user_with_subscription'
    ),
    url(
        r'^test_command/$',
        TestCommandApiView.as_view(),
        name='test_command'
    ),
    url(
        r'^test_command_payment/$',
        TestPaymentCommandApiView.as_view(),
        name='test_command_payment'
    ),
    url(
        r'^test_webhook_piano/$',
        TestWebhookPianoApiView.as_view(),
        name='test_command'
    ),
]
