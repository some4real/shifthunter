from zoneinfo import ZoneInfo

from .shyftr import normalize_shifts


def normalize_site_name(value):
    value = (value or "").strip().lower()

    # Shyftr may prefix site names with an organization/category.
    prefixes = (
        "dhs - ",
        "dhs-",
    )

    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix):].strip()
            break

    return " ".join(value.split())


def site_matches(shift_site, preference):
    site = normalize_site_name(shift_site)

    primary = normalize_site_name(
        preference.priority_site
    )

    if site == primary:
        return True

    secondary = [
        normalize_site_name(item)
        for item in (preference.secondary_sites or "").split(",")
        if item.strip()
    ]

    return site in secondary


def time_matches(shift, preference):
    if not shift["start_at"] or not shift["end_at"]:
        return False

    tz = ZoneInfo(preference.timezone)

    start = shift["start_at"].astimezone(tz)
    end = shift["end_at"].astimezone(tz)

    if start.weekday() != preference.weekday:
        return False

    window_start = preference.start_time
    window_end = preference.end_time

    shift_start = start.time().replace(tzinfo=None)
    shift_end = end.time().replace(tzinfo=None)

    if window_start <= window_end:
        return (
            shift_start >= window_start
            and shift_end <= window_end
        )

    # Overnight window, e.g. 22:00 -> 06:00.
    return (
        shift_start >= window_start
        or shift_end <= window_end
    )


def score_shift(shift, preference):
    score = 0
    reasons = []

    site = normalize_site_name(shift["site"])
    primary = normalize_site_name(
        preference.priority_site
    )

    if site == primary:
        score += 50
        reasons.append(
            f"priority site: {preference.priority_site}"
        )
    elif site_matches(shift["site"], preference):
        score += 25
        reasons.append("secondary site")

    if time_matches(shift, preference):
        score += 30
        reasons.append(
            "preferred weekday/time window"
        )

    if shift["hours"] >= float(
        preference.minimum_hours
    ):
        score += 20
        reasons.append(
            f"minimum hours met ({shift['hours']:.2f}h)"
        )

    if (
        preference.minimum_value > 0
        and shift["value"] is not None
        and shift["value"]
        >= float(preference.minimum_value)
    ):
        score += 10
        reasons.append("minimum value met")

    if preference.require_autoassignable:
        if shift["autoassignable"]:
            score += 10
            reasons.append("autoassignable")
        else:
            return 0, ["not autoassignable"]

    return score, reasons


def match_shifts(raw_shifts, preference):
    normalized = normalize_shifts(raw_shifts)

    matches = []

    from django.utils import timezone

    now = timezone.now()

    for shift in normalized:
        if not shift["end_at"]:
            continue

        if shift["end_at"] <= now:
            continue

        if not site_matches(
            shift["site"],
            preference,
        ):
            continue

        if not time_matches(
            shift,
            preference,
        ):
            continue

        if shift["hours"] < float(
            preference.minimum_hours
        ):
            continue

        if (
            preference.minimum_value > 0
            and (
                shift["value"] is None
                or shift["value"]
                < float(preference.minimum_value)
            )
        ):
            continue

        score, reasons = score_shift(
            shift,
            preference,
        )

        if score < preference.minimum_match_score:
            continue

        shift["match_score"] = score
        shift["match_reason"] = "; ".join(
            reasons
        )

        matches.append(shift)

    return normalized, matches
