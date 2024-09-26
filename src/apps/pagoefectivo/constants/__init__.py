from django.conf import settings

try:
    if settings.ENVIRONMENT == 'test':
        from .test import *
    elif settings.ENVIRONMENT == 'production':
        from .production import *
except ImportError:
    pass
