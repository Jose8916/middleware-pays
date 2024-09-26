"""
    Parámetros de configuración de Siebel
"""
from django.conf import settings


PAYWALL_SIEBEL_COMISIONES_URL = getattr(
    settings,
    'PAYWALL_SIEBEL_COMISIONES_URL',
    'http://200.4.199.84'
)
