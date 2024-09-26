from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.authtoken.views import obtain_auth_token
from django.conf.urls.static import static


urlpatterns = [
    # APIs

    # path(
    #     '',
    #     include('apps.autogestion.urls') # XXX Autogestión
    # ),
    path(
        'api/',
        include('apps.paywall.api.public')
    ),
    path(
        'api/siebel/',
        include('apps.siebel.urls')
    ),
    path(
        'data/',
        include('apps.data.urls')
    ),
    path(
        'events/api/',
        include('apps.paywall.api.private')
    ),
    path(
        'notifications/api/',
        include('apps.pagoefectivo.api.private')
    ),
    #path(
    #    'pe/api/',
    #    include('apps.pagoefectivo.api.public')
    #),

    path(
        'admin/',
        admin.site.urls
    ),
    path(
        'admin/paywall/',
        include('apps.paywall.urls')
    ),
]


if settings.ENVIRONMENT != 'production':
    schema_view = get_schema_view(
        openapi.Info(
            title="Paywall • Middleware",
            default_version='v0.9',
            description="APIs de integración de paywall-middleware.",
            # terms_of_service="https://www.google.com/policies/terms/",
            # contact=openapi.Contact(email="contact@snippets.local"),
            # license=openapi.License(name="BSD License"),
        ),
        public=True,
        permission_classes=(permissions.IsAuthenticated, ),
    )

    urlpatterns = [
        path(
            '',
            RedirectView.as_view(url='/admin/', permanent=False),
            name="index"
        ),
        # API
        path(
            'api-token-auth/',
            obtain_auth_token,
            name='api_token_auth'
        ),
        # DOCS
        url(
            r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'
        ),
        url(
            r'^swagger/$',
            schema_view.with_ui('swagger', cache_timeout=0),
            name='schema-swagger-ui'
        ),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + urlpatterns


if settings.DEBUG:
    try:
        import debug_toolbar
    except Exception:
        pass
    else:
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns


admin.site.site_header = 'Paywall • Middleware'
admin.site.site_title = 'Paywall • Middleware'
