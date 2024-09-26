from apps.paywall.models import Subscription, SubscriptionState
from apps.arcsubs.utils import timestamp_to_datetime
from sentry_sdk import capture_exception


class HistoryState(object):
    def __init__(self, subscription):
        self.subscription = subscription

    def update_data(self):
        if self.subscription.data:
            events_list = self.subscription.data.get('events', '')
            previous_event = ''

            for event in range(len(events_list)):
                try:
                    next_event = events_list[event + 1].get('eventType', '')
                except Exception as e:
                    next_event = ''

                try:
                    if previous_event != 'SUSPEND_SUBSCRIPTION' and next_event != 'SUSPEND_SUBSCRIPTION'\
                            and previous_event != 'FAIL_RENEW_SUBSCRIPTION'\
                            and events_list[event].get('eventType', '') == 'FAIL_RENEW_SUBSCRIPTION' and previous_event:
                        value_state = 4
                        event_type = 'SUSPEND_SUBSCRIPTION'
                    else:
                        state_subscription = {
                            'START_SUBSCRIPTION': 1,
                            'TERMINATE_SUBSCRIPTION': 2,
                            'CANCEL_SUBSCRIPTION': 3,
                            'SUSPEND_SUBSCRIPTION': 4,
                            'RENEW_SUBSCRIPTION': 1
                        }
                        value_state = state_subscription.get(events_list[event].get('eventType', ''), '')
                        event_type = events_list[event].get('eventType', '')

                    if value_state:
                        if not SubscriptionState.objects.filter(
                                date_timestamp=events_list[event].get('eventDateUTC'),
                                event_type=event_type,
                                subscription=self.subscription
                        ).exists():
                            sub_state = SubscriptionState(
                                state=value_state,
                                event_type=event_type,
                                date=timestamp_to_datetime(events_list[event].get('eventDateUTC', '')),
                                detail=events_list[event].get('details', ''),
                                subscription=self.subscription,
                                date_timestamp=events_list[event].get('eventDateUTC')
                            )
                            sub_state.save()
                    previous_event = events_list[event].get('eventType', '')

                except Exception:
                    capture_exception()
                except SystemExit:
                    capture_exception()
