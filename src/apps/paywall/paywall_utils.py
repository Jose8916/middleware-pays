from sentry_sdk import capture_event

from ..arcsubs.models import ArcUser
from .arc_clients import IdentityClient


def get_arc_user_by_token(request=None, token=None, site='gestion'):
    """
        Valida el JWT de arc y retorna un objeto ArcUser.
        Headers:
            - [site]: Portal
            - [user-token]: JWT
    """

    if request:
        user_token = request.META.get('HTTP_USER_TOKEN', token)
        arc_site = request.headers.get('site', site)
    else:
        user_token = token
        arc_site = site

    profile = IdentityClient().get_profile_by_token(
        token=user_token,
        site=arc_site,
    )

    if profile:
        return ArcUser.objects.get_by_uuid(
            uuid=profile['uuid'],
            data=profile,
        )

    else:
        capture_event(
            {
                'message': 'get_arc_user_by_token error: Session expired',
                'extra': {
                    'jwt': user_token,
                    'site': arc_site,
                    'profile': profile,
                }
            }
        )
