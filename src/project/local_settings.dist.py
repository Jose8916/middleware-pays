##########
# DJANGO #
##########

DEBUG = False

ALLOWED_HOSTS = ['test.paywall.comerciosuscripciones.pe', ]

ENVIRONMENT = 'test'

SENTRY_DNS = 'https://5c710c4738934c48bd8cc3fa20a35d74@sentry.ec.pe/66'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'middleware_prod_viernes',
        'USER': 'postgres',
        'PASSWORD': '123',
        'HOST': 'localhost',
        'PORT': '5432',
    },
}

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'juan.perez@gmail.com'
EMAIL_HOST_PASSWORD = '*****'
EMAIL_PORT = 587

MANAGERS = ['qaelcomercio@gmail.com', ]


###########
# PAYWALL #
###########

PAYWALL_CONTACT_US = ['qaelcomercio@gmail.com', ]

# SIEBEL
PAYWALL_SIEBEL_IP = 'http://200.4.199.84'
PAYWALL_SIEBEL_URL = 'http://200.4.199.84/wssuscripcionsiebel/'

# ARC
PAYWALL_ARC_PUBLIC_URL = 'https://api-sandbox.{site}.pe'
PAYWALL_ARC_TOKEN = '56V58QFSB7EC6DC6EAFUDC34S04T4L18pnJapmry/XUSQSmXuTFWu4ZfJlYHcL9+EP98++sT'
PAYWALL_ARC_URL = 'https://api.sandbox.elcomercio.arcpublishing.com/'

# CLUB
PAYWALL_CLUB_URL = 'https://pre.2.clubelcomercio.pe'
PAYWALL_CLUB_KEY = 'c4f0521828d00aa3609047c0460dc01a'
PAYWALL_CLUB_TOKEN = 'c4f0521828d00aa3609047c0460dc01a'

# MAILING
PAYWALL_MAILING_ASSETS_URL = 'http://mailing.ecomedia.pe/'
PAYWALL_MAILING_SENDER = 'robot@ec.pe'
