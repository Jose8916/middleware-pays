from apps.paywall.models import EventReport, Subscription
from sentry_sdk import capture_exception


class EventReportClass(object):
    def save_event_report(self, events, site):
        for obj in events:
            print(obj)
            print(obj.get('eventId', ''))
            print(obj.get('eventType', ''))
            if not EventReport.objects.filter(
                event_id=obj.get('eventId', ''),
                event_type=obj.get('eventType', '')
            ).exists():
                try:
                    subcription_obj = Subscription.objects.get(arc_id=obj.get('subscriptionId', ''))
                except Exception:
                    subcription_obj = None

                try:
                    event_report = EventReport(
                        current_product_name=obj.get('currentProductName', ''),
                        event_id=obj.get('eventId', ''),
                        client_id=obj.get('clientId', ''),
                        event_type=obj.get('eventType', ''),
                        subscription_id=obj.get('subscriptionId', ''),
                        created_on=obj.get('createdOn', ''),
                        current_product_sku=obj.get('currentProductSKU', ''),
                        current_product_price_code=obj.get('currentProductPriceCode', ''),
                        data=obj,
                        subscription_obj=subcription_obj,
                        site=site,
                    )
                    event_report.save()
                except Exception:
                    capture_exception()


