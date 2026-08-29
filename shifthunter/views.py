import json
import os
from datetime import datetime, timezone, time

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import (
    AutoPickSettings,
    PushSubscription,
    UserPreference,
)
from .services.shyftr import ShyftrClient, ShyftrError


def _parse_time(time_str):
    """Parse time string (HH:MM) to time object."""
    if isinstance(time_str, time):
        return time_str
    if not isinstance(time_str, str):
        raise ValueError(f"Expected string or time object, got {type(time_str)}")
    try:
        dt = datetime.strptime(time_str.strip(), "%H:%M")
        return dt.time()
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")


def dashboard(request):
    return render(
        request,
        "shifthunter/dashboard.html",
        {
            "vapid_public_key": os.getenv(
                "VAPID_PUBLIC_KEY",
                "",
            ).strip(),
        },
    )


def _get_preference():
    preference = UserPreference.objects.first()

    if preference is None:
        preference = UserPreference.objects.create()

    return preference


def _get_auto_pick(preference):
    auto_pick, _ = AutoPickSettings.objects.get_or_create(
        preference=preference,
        defaults={
            "enabled": False,
            "weekday": preference.weekday,
            "start_time": preference.start_time,
            "end_time": preference.end_time,
            "minimum_hours": preference.minimum_hours,
            "minimum_value": preference.minimum_value,
            "require_autoassignable": preference.require_autoassignable,
            "minimum_match_score": preference.minimum_match_score,
            "secondary_sites": preference.secondary_sites,
        },
    )

    return auto_pick


def _preferences_response(preference, auto_pick):
    return {
        "monitoring": {
            "enabled": preference.monitoring_enabled,
            "priority_site": preference.priority_site,
            "secondary_sites": preference.secondary_sites,
            "weekday": preference.weekday,
            "start_time": preference.start_time.strftime("%H:%M"),
            "end_time": preference.end_time.strftime("%H:%M"),
            "timezone": preference.timezone,
            "minimum_hours": str(preference.minimum_hours),
            "minimum_value": str(preference.minimum_value),
            "minimum_match_score": preference.minimum_match_score,
            "require_autoassignable": preference.require_autoassignable,
            "push_enabled": preference.push_enabled,
            "email_enabled": preference.email_enabled,
            "email_address": preference.email_address,
            "email_verified": preference.email_verified,
        },
        "auto_pick": {
            "enabled": auto_pick.enabled,
            "secondary_sites": auto_pick.secondary_sites,
            "weekday": auto_pick.weekday,
            "start_time": auto_pick.start_time.strftime("%H:%M"),
            "end_time": auto_pick.end_time.strftime("%H:%M"),
            "minimum_hours": str(auto_pick.minimum_hours),
            "minimum_value": str(auto_pick.minimum_value),
            "shift_type": auto_pick.shift_type,
            "require_autoassignable": auto_pick.require_autoassignable,
            "minimum_match_score": auto_pick.minimum_match_score,
            "secondary_sites": auto_pick.secondary_sites,
        },
        "auto_pick_endpoint_configured": bool(
            os.getenv("SHYFTR_AUTO_PICK_ENDPOINT", "").strip()
        ),
    }


@require_http_methods(["GET"])
def preferences_api(request):
    preference = _get_preference()
    auto_pick = _get_auto_pick(preference)

    return JsonResponse(
        _preferences_response(
            preference,
            auto_pick,
        )
    )


@csrf_exempt
@require_http_methods(["POST"])
def preferences_update_api(request):
    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON request."},
            status=400,
        )

    preference = _get_preference()
    auto_pick = _get_auto_pick(preference)

    monitoring = payload.get("monitoring", {})
    auto_data = payload.get("auto_pick", {})

    try:
        # =========================
        # Monitoring settings
        # =========================

        if "enabled" in monitoring:
            preference.monitoring_enabled = bool(
                monitoring["enabled"]
            )

        if "priority_site" in monitoring:
            preference.priority_site = str(
                monitoring["priority_site"]
            ).strip()

        if "secondary_sites" in monitoring:
            preference.secondary_sites = str(
                monitoring["secondary_sites"]
            ).strip()

        if "weekday" in monitoring:
            preference.weekday = int(
                monitoring["weekday"]
            )

        if "start_time" in monitoring:
            preference.start_time = _parse_time(monitoring["start_time"])

        if "end_time" in monitoring:
            preference.end_time = _parse_time(monitoring["end_time"])

        if "minimum_hours" in monitoring:
            preference.minimum_hours = monitoring["minimum_hours"]

        if "minimum_value" in monitoring:
            preference.minimum_value = monitoring["minimum_value"]

        if "minimum_match_score" in monitoring:
            preference.minimum_match_score = int(
                monitoring["minimum_match_score"]
            )

        if "require_autoassignable" in monitoring:
            preference.require_autoassignable = bool(
                monitoring["require_autoassignable"]
            )

        if "push_enabled" in monitoring:
            preference.push_enabled = bool(
                monitoring["push_enabled"]
            )

        if "email_enabled" in monitoring:
            preference.email_enabled = bool(
                monitoring["email_enabled"]
            )

        if "email_address" in monitoring:
            preference.email_address = str(
                monitoring["email_address"]
            ).strip()

        preference.save()

        # =========================
        # Auto-Pick settings
        # =========================

        if "enabled" in auto_data:
            auto_pick.enabled = bool(
                auto_data["enabled"]
            )

        if "secondary_sites" in auto_data:
            auto_pick.secondary_sites = str(
                auto_data["secondary_sites"]
            ).strip()

        if "weekday" in auto_data:
            auto_pick.weekday = int(
                auto_data["weekday"]
            )

        if "start_time" in auto_data:
            auto_pick.start_time = _parse_time(auto_data["start_time"])

        if "end_time" in auto_data:
            auto_pick.end_time = _parse_time(auto_data["end_time"])

        if "minimum_hours" in auto_data:
            auto_pick.minimum_hours = auto_data["minimum_hours"]

        if "minimum_value" in auto_data:
            auto_pick.minimum_value = auto_data["minimum_value"]

        if "shift_type" in auto_data:
            auto_pick.shift_type = str(
                auto_data["shift_type"]
            )

        if "require_autoassignable" in auto_data:
            auto_pick.require_autoassignable = bool(
                auto_data["require_autoassignable"]
            )

        if "minimum_match_score" in auto_data:
            auto_pick.minimum_match_score = int(
                auto_data["minimum_match_score"]
            )

        auto_pick.save()

        return JsonResponse(
            {
                "saved": True,
                **_preferences_response(
                    preference,
                    auto_pick,
                ),
            }
        )

    except (ValueError, TypeError) as e:
        return JsonResponse(
            {"error": f"Invalid data format: {str(e)}"},
            status=400,
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to save settings: {str(e)}"},
            status=500,
        )


def _number(value):
    try:
        number = float(value)

        if number == number and number not in (
            float("inf"),
            float("-inf"),
        ):
            return number

    except (TypeError, ValueError):
        pass

    return None


def _normalize(shift):
    location = str(
        shift.get("bubo_contract_location_name")
        or shift.get("location")
        or "Unknown location"
    )

    start = str(
        shift.get("start_timestamp")
        or shift.get("start")
        or shift.get("start_date")
        or ""
    )

    end = str(
        shift.get("end_timestamp")
        or shift.get("end")
        or shift.get("end_date")
        or ""
    )

    if start and len(start) == 10:
        start = f"{start}T00:00:00Z"

    if end and len(end) == 10:
        end = f"{end}T08:00:00Z"

    try:
        hours = (
            datetime.fromisoformat(
                end.replace("Z", "+00:00")
            )
            - datetime.fromisoformat(
                start.replace("Z", "+00:00")
            )
        ).total_seconds() / 3600

    except (ValueError, TypeError):
        hours = 0

    try:
        weekday = datetime.fromisoformat(
            start.replace("Z", "+00:00")
        ).weekday()

    except (ValueError, TypeError):
        weekday = -1

    primary = (
        location.lower().strip()
        in {
            "151 east",
            "dhs - 151 east",
        }
    )

    return {
        "id": str(
            shift.get("bubo_shift_id")
            or shift.get("id")
            or f"{location}-{start}"
        ),
        "location": location,
        "start": start,
        "end": end,
        "schedule": str(
            shift.get("schedule_type")
            or shift.get("shift_type")
            or "Unknown"
        ),
        "pay": _number(
            shift.get("estimated_total_pay")
        ),
        "distance": _number(
            shift.get("distance")
        ),
        "autoassignable": bool(
            shift.get("is_autoassignable")
        ),
        "status": str(
            shift.get("status")
            or "Available"
        ).lower(),
        "priority": (
            "primary"
            if primary
            and (
                weekday == 2
                or not start
                or hours == 8
            )
            else "normal"
        ),
    }


@require_http_methods(["GET"])
def shifts_api(request):
    try:
        shifts = ShyftrClient().fetch_shifts()

        return JsonResponse(
            {
                "shifts": [
                    _normalize(item)
                    for item in shifts
                    if isinstance(item, dict)
                ],
                "source": "shyftr",
                "checkedAt": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
        )

    except ShyftrError as error:
        return JsonResponse(
            {"error": str(error)},
            status=503,
        )


@csrf_exempt
@require_http_methods(["POST"])
def push_subscription_api(request):
    try:
        data = json.loads(
            request.body or "{}"
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400,
        )

    endpoint = str(
        data.get("endpoint", "")
    ).strip()

    keys = data.get("keys", {})

    p256dh = str(
        keys.get("p256dh", "")
    ).strip()

    auth = str(
        keys.get("auth", "")
    ).strip()

    if not endpoint or not p256dh or not auth:
        return JsonResponse(
            {"error": "Invalid push subscription."},
            status=400,
        )

    subscription, created = (
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "p256dh": p256dh,
                "auth": auth,
                "active": True,
            },
        )
    )

    return JsonResponse(
        {
            "ok": True,
            "created": created,
        }
    )
