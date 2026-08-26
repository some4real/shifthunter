from django.core.management.base import BaseCommand
from django.utils import timezone
from shifthunter.services.alerts import deliver_pending_alerts

from shifthunter.models import (
    AlertDelivery,
    PollRun,
    Shift,
    UserPreference,
)
from shifthunter.services.matcher import match_shifts
from shifthunter.services.shyftr import (
    ShyftrClient,
    ShyftrError,
)


class Command(BaseCommand):
    help = "Run one Shyftr polling cycle."

    def handle(self, *args, **options):
        poll = PollRun.objects.create()

        try:
            preference = UserPreference.objects.first()

            if preference is None:
                preference = UserPreference.objects.create()

            if not preference.monitoring_enabled:
                poll.success = True
                poll.finished_at = timezone.now()
                poll.save(
                    update_fields=[
                        "success",
                        "finished_at",
                    ]
                )

                self.stdout.write(
                    self.style.WARNING(
                        "Monitoring is disabled."
                    )
                )
                return

            self.stdout.write("Polling Shyftr...")

            client = ShyftrClient()
            raw_shifts = client.fetch_shifts()

            poll.shifts_received = len(raw_shifts)

            normalized, matches = match_shifts(
                raw_shifts,
                preference,
            )

            poll.shifts_normalized = len(normalized)
            poll.shifts_matched = len(matches)

            new_alerts = 0

            for data in normalized:
                shift, _ = Shift.objects.update_or_create(
                    shyftr_id=data["shyftr_id"],
                    defaults={
                        "site": data["site"],
                        "shift_date": data["shift_date"],
                        "start_time": data["start_time"],
                        "end_time": data["end_time"],
                        "start_at": data["start_at"],
                        "end_at": data["end_at"],
                        "hours": data["hours"],
                        "shift_type": data["shift_type"],
                        "value": data["value"],
                        "distance": data["distance"],
                        "autoassignable": data[
                            "autoassignable"
                        ],
                        "status": data["status"],
                        "raw_data": data["raw_data"],
                        "is_available": True,
                    },
                )

                matching = next(
                    (
                        item
                        for item in matches
                        if item["shyftr_id"]
                        == data["shyftr_id"]
                    ),
                    None,
                )

                if matching is None:
                    continue

                self.stdout.write(
                    self.style.SUCCESS(
                        f"MATCH: {data['shyftr_id']} | "
                        f"{data['site']} | "
                        f"{data['start_at']} -> "
                        f"{data['end_at']}"
                    )
                )

                # Create a push delivery record only once.
                if preference.push_enabled:
                    delivery, created = (
                        AlertDelivery.objects.get_or_create(
                            shift=shift,
                            channel=AlertDelivery.CHANNEL_PUSH,
                            defaults={
                                "status": (
                                    AlertDelivery.STATUS_PENDING
                                )
                            },
                        )
                    )

                    if created:
                        new_alerts += 1
                        self.stdout.write(
                            self.style.WARNING(
                                "NEW PUSH ALERT: "
                                f"{shift.shyftr_id}"
                            )
                        )

                # Create an email delivery record only once.
                if (
                    preference.email_enabled
                    and preference.email_verified
                    and preference.email_address
                ):
                    delivery, created = (
                        AlertDelivery.objects.get_or_create(
                            shift=shift,
                            channel=AlertDelivery.CHANNEL_EMAIL,
                            defaults={
                                "status": (
                                    AlertDelivery.STATUS_PENDING
                                )
                            },
                        )
                    )

                    if created:
                        new_alerts += 1
                        self.stdout.write(
                            self.style.WARNING(
                                "NEW EMAIL ALERT: "
                                f"{shift.shyftr_id}"
                            )
                        )

            poll.new_matches = new_alerts
            poll.success = True
            poll.finished_at = timezone.now()

            poll.save(
                update_fields=[
                    "finished_at",
                    "success",
                    "shifts_received",
                    "shifts_normalized",
                    "shifts_matched",
                    "new_matches",
                    "error_message",
                ]
            )

            alert_results = deliver_pending_alerts()

            self.stdout.write(
                self.style.SUCCESS(
                    "Alerts delivered: "
                    f"{alert_results['push_sent']} push, "
                    f"{alert_results['email_sent']} email, "
                    f"{alert_results['failed']} failed."
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Poll complete: "
                    f"{poll.shifts_received} received, "
                    f"{poll.shifts_normalized} normalized, "
                    f"{poll.shifts_matched} matched, "
                    f"{poll.new_matches} new alerts."
                )
            )

        except ShyftrError as error:
            poll.success = False
            poll.finished_at = timezone.now()
            poll.error_message = str(error)

            poll.save(
                update_fields=[
                    "success",
                    "finished_at",
                    "error_message",
                ]
            )

            self.stderr.write(
                self.style.ERROR(str(error))
            )

        except Exception as error:
            poll.success = False
            poll.finished_at = timezone.now()
            poll.error_message = str(error)

            poll.save(
                update_fields=[
                    "success",
                    "finished_at",
                    "error_message",
                ]
            )

            self.stderr.write(
                self.style.ERROR(
                    f"Unexpected polling error: {error}"
                )
            )
