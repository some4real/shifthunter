from django.db import models


class UserPreference(models.Model):
    WEEKDAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    TIMEZONE_CHOICES = [
        ("America/New_York", "America/New_York"),
    ]

    priority_site = models.CharField(
        max_length=255,
        default="151 East",
    )

    secondary_sites = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated secondary site names.",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        default=2,
    )

    start_time = models.TimeField(default="00:00")
    end_time = models.TimeField(default="08:00")

    timezone = models.CharField(
        max_length=64,
        choices=TIMEZONE_CHOICES,
        default="America/New_York",
    )

    minimum_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8,
    )

    minimum_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    minimum_match_score = models.PositiveSmallIntegerField(
        default=0,
    )

    require_autoassignable = models.BooleanField(
        default=False,
    )

    monitoring_enabled = models.BooleanField(
        default=True,
    )

    push_enabled = models.BooleanField(
        default=True,
    )

    email_enabled = models.BooleanField(
        default=False,
    )

    email_address = models.EmailField(
        blank=True,
        default="",
    )

    email_verified = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.priority_site} monitoring preferences"


class Shift(models.Model):
    shyftr_id = models.CharField(
        max_length=255,
        unique=True,
    )

    site = models.CharField(max_length=255)

    shift_date = models.DateField(
        null=True,
        blank=True,
    )

    start_time = models.TimeField(
        null=True,
        blank=True,
    )

    end_time = models.TimeField(
        null=True,
        blank=True,
    )

    start_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    end_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    shift_type = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    distance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    autoassignable = models.BooleanField(default=False)

    status = models.CharField(
        max_length=100,
        default="Available",
    )

    raw_data = models.JSONField(
        default=dict,
        blank=True,
    )

    first_seen_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_seen_at = models.DateTimeField(
        auto_now=True,
    )

    is_available = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return (
            f"{self.shyftr_id} - "
            f"{self.site} - "
            f"{self.shift_date}"
        )


class PollRun(models.Model):
    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    success = models.BooleanField(
        default=False,
    )

    shifts_received = models.PositiveIntegerField(
        default=0,
    )

    shifts_normalized = models.PositiveIntegerField(
        default=0,
    )

    shifts_matched = models.PositiveIntegerField(
        default=0,
    )

    new_matches = models.PositiveIntegerField(
        default=0,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    def __str__(self):
        status = "success" if self.success else "failed"
        return f"Poll {self.started_at} - {status}"


class AlertDelivery(models.Model):
    CHANNEL_PUSH = "push"
    CHANNEL_EMAIL = "email"

    CHANNEL_CHOICES = [
        (CHANNEL_PUSH, "Browser Push"),
        (CHANNEL_EMAIL, "Email"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="alert_deliveries",
    )

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "channel"],
                name="unique_shift_alert_channel",
            )
        ]

    def __str__(self):
        return (
            f"{self.shift.shyftr_id} - "
            f"{self.channel} - "
            f"{self.status}"
        )


class PushSubscription(models.Model):
    endpoint = models.TextField(
        unique=True,
    )

    p256dh = models.TextField()
    auth = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.endpoint[:80]

class AutoPickSettings(models.Model):
    SHIFT_TYPE_CHOICES = [
        ("", "Any shift type"),
        ("Grave", "Grave"),
        ("Day", "Day"),
        ("Evening", "Evening"),
    ]

    preference = models.OneToOneField(
        UserPreference,
        on_delete=models.CASCADE,
        related_name="auto_pick",
    )

    enabled = models.BooleanField(
        default=False,
    )

    secondary_sites = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated additional sites allowed for Auto-Pick.",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=UserPreference.WEEKDAY_CHOICES,
        default=2,
    )

    start_time = models.TimeField(
        default="00:00",
    )

    end_time = models.TimeField(
        default="08:00",
    )

    minimum_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8,
    )

    minimum_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    shift_type = models.CharField(
        max_length=100,
        choices=SHIFT_TYPE_CHOICES,
        blank=True,
        default="Grave",
    )

    require_autoassignable = models.BooleanField(
        default=False,
    )

    minimum_match_score = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        return f"Auto-Pick {status} - {self.preference.priority_site}"

class AutoPickAttempt(models.Model):
    RESULT_NOT_CONFIGURED = "not_configured"
    RESULT_SUCCESS = "success"
    RESULT_FAILED = "failed"

    RESULT_CHOICES = [
        (RESULT_NOT_CONFIGURED, "Not configured"),
        (RESULT_SUCCESS, "Success"),
        (RESULT_FAILED, "Failed"),
    ]

    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name="auto_pick_attempts",
    )

    result = models.CharField(
        max_length=30,
        choices=RESULT_CHOICES,
    )

    message = models.TextField(
        blank=True,
        default="",
    )

    attempted_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"Auto-Pick {self.shift.shyftr_id} "
            f"- {self.result}"
        )