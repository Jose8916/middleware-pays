from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import get_template
from sentry_sdk import capture_exception, capture_event


def render_send_email(
        template_name,
        subject,
        to_emails,
        from_email=None,
        cc_emails=None,
        bcc_emails=None,
        context=None):

    if isinstance(to_emails, str):
        to_emails = [to_emails, ]

    # # Si no existe el template, notificar por sentry.
    template = get_template(template_name)

    html = template.render(context or {})

    # if getattr(settings, 'ENVIRONMENT') == 'test':
    bcc_emails = settings.MANAGERS

    email = EmailMessage(
        subject=subject,
        body=html,
        from_email=from_email or settings.PAYWALL_MAILING_SENDER,
        to=to_emails,
        cc=cc_emails,
        bcc=bcc_emails,
    )

    email.content_subtype = "html"

    try:
        email.send(fail_silently=True)

    except (Exception, SystemExit):
        capture_exception()
