import os

from django.core.mail import send_mail
from django.utils import timezone
from pywebpush import webpush, WebPushException

from shifthunter.models import AlertDelivery, PushSubscription


def shift_message(shift):
    date = shift.shift_date.strftime("%a, %b %-d") if shift.shift_date else "Unknown date"

    start = shift.start_time.strftime("%-I:%M %p") if shift.start_time else "?"
    end = shift.end_time.strftime("%-I:%M %p") if shift.end_time else "?"

    pay = (
        f"${shift.value:.2f}"
        if shift.value is not None
        else "Pay unavailable"
    )

    return (
        f"{shift.site}\n"
        f"{date}\n"
        f"{start} – {end}\n"
        f"{shift.hours:.2f} hours\n"
        f"{pay}"
    )


def send_push_alert(delivery):
    subscriptions = PushSubscription.objects.filter(active=True)

    if not subscriptions.exists():
        delivery.status = AlertDelivery.STATUS_FAILED
        delivery.error_message = "No active push subscriptions."
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=["status", "error_message", "sent_at"])
        return False

    private_key = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    subject = os.getenv("VAPID_CLAIMS_SUB", "").strip()

    if not private_key or not subject:
        delivery.status = AlertDelivery.STATUS_FAILED
        delivery.error_message = "VAPID_PRIVATE_KEY or VAPID_CLAIMS_SUB is not configured."
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=["status", "error_message", "sent_at"])
        return False

    payload = {
        "title": "Shyftr shift available",
        "body": shift_message(delivery.shift),
        "shift_id": delivery.shift.shyftr_id,
        "site": delivery.shift.site,
    }

    success = False
    errors = []

    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=__import__("json").dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={
                    "sub": subject,
                },
            )

            success = True

        except WebPushException as error:
            errors.append(str(error))

            # Subscription is no longer usable.
            if getattr(error, "response", None) is not None:
                if error.response.status_code in (404, 410):
                    subscription.active = False
                    subscription.save(update_fields=["active"])

    if success:
        delivery.status = AlertDelivery.STATUS_SENT
        delivery.sent_at = timezone.now()
        delivery.error_message = ""
    else:
        delivery.status = AlertDelivery.STATUS_FAILED
        delivery.sent_at = timezone.now()
        delivery.error_message = "; ".join(errors)[:5000]

    delivery.save(
        update_fields=[
            "status",
            "sent_at",
            "error_message",
        ]
    )

    return success


def send_email_alert(delivery):
    preference = delivery.shift

    # The delivery record itself does not contain the email address,
    # so import the preference here.
    from shifthunter.models import UserPreference

    user_preference = UserPreference.objects.first()

    if (
        user_preference is None
        or not user_preference.email_enabled
        or not user_preference.email_verified
        or not user_preference.email_address
    ):
        delivery.status = AlertDelivery.STATUS_FAILED
        delivery.error_message = "Email notifications are not configured or verified."
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=["status", "error_message", "sent_at"])
        return False

    shift = delivery.shift

    subject = (
        f"Shyftr shift available — {shift.site}"
    )

    body = (
        "A monitored Shyftr shift is available.\n\n"
        f"{shift_message(shift)}\n\n"
        f"Shift ID: {shift.shyftr_id}\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=os.getenv(
                "DEFAULT_FROM_EMAIL",
                user_preference.email_address,
            ),
            recipient_list=[
                user_preference.email_address,
            ],
            fail_silently=False,
        )

        delivery.status = AlertDelivery.STATUS_SENT
        delivery.sent_at = timezone.now()
        delivery.error_message = ""

        delivery.save(
            update_fields=[
                "status",
                "sent_at",
                "error_message",
            ]
        )

        return True

    except Exception as error:
        delivery.status = AlertDelivery.STATUS_FAILED
        delivery.sent_at = timezone.now()
        delivery.error_message = str(error)[:5000]

        delivery.save(
            update_fields=[
                "status",
                "sent_at",
                "error_message",
            ]
        )

        return False


def deliver_pending_alerts():
    deliveries = AlertDelivery.objects.filter(
        status=AlertDelivery.STATUS_PENDING
    ).select_related("shift")

    results = {
        "push_sent": 0,
        "email_sent": 0,
        "failed": 0,
    }

    for delivery in deliveries:
        if delivery.channel == AlertDelivery.CHANNEL_PUSH:
            if send_push_alert(delivery):
                results["push_sent"] += 1
            else:
                results["failed"] += 1

        elif delivery.channel == AlertDelivery.CHANNEL_EMAIL:
            if send_email_alert(delivery):
                results["email_sent"] += 1
            else:
                results["failed"] += 1

    return results
