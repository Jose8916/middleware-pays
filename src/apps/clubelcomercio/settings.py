"""
    Parámetros de configuración de Club El Comercio
"""
from django.conf import settings


PAYWALL_CLUB_URL = getattr(
    settings,
    'PAYWALL_CLUB_URL',
    'https://pre.2.clubelcomercio.pe'
)

PAYWALL_CLUB_TOKEN = getattr(
    settings,
    'PAYWALL_CLUB_TOKEN',
    'c4f0521828d00aa3609047c0460dc01a'
)

# XXX Quitar hardcode cuando configuren settings
# PAYWALL_CLUB_TOKEN = 'c4f0521828d00aa3609047c0460dc01a'
