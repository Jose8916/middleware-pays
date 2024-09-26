from django.conf import settings


def get_environment(request):
    return {
        'ENVIROMENT': settings.ENVIRONMENT
    }
