import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ShyftrError(Exception):
    """Raised when the Shyftr API cannot be reached or understood."""


class ShyftrClient:
    def __init__(self):
        self.token = os.getenv("SHYFTR_TOKEN", "").strip()
        self.endpoint = os.getenv(
            "SHYFTR_SHIFT_ENDPOINT",
            "https://api.bubo.io/shyftr/shift",
        )
        self.timeout = int(os.getenv("SHYFTR_TIMEOUT", "15"))

    def fetch_shifts(self):
        if not self.token:
            raise ShyftrError("SHYFTR_TOKEN is not configured.")

        credential = self.token.removeprefix("Bearer ").removeprefix("bearer ")

        request = Request(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {credential}",
                "Accept": "application/json, text/plain, */*",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except HTTPError as error:
            if error.code in (401, 403):
                raise ShyftrError(
                    "Shyftr rejected the configured token."
                ) from error

            raise ShyftrError(
                f"Shyftr returned HTTP {error.code}."
            ) from error

        except URLError as error:
            raise ShyftrError(
                "Unable to reach Shyftr."
            ) from error

        except TimeoutError as error:
            raise ShyftrError(
                "Shyftr request timed out."
            ) from error

        except json.JSONDecodeError as error:
            raise ShyftrError(
                "Shyftr returned invalid JSON."
            ) from error

        return self._extract_shifts(payload)

    def _extract_shifts(self, payload):
        if isinstance(payload, list):
            return [
                item
                for item in payload
                if isinstance(item, dict)
            ]

        if not isinstance(payload, dict):
            return []

        collections = [
            "unassigned_shifts",
            "current_shifts",
            "available_shifts",
        ]

        shifts = []

        for key in collections:
            value = payload.get(key, [])

            if isinstance(value, list):
                shifts.extend(
                    item
                    for item in value
                    if isinstance(item, dict)
                )

        if shifts:
            return shifts

        for key in ("shifts", "data"):
            value = payload.get(key)

            if isinstance(value, list):
                return [
                    item
                    for item in value
                    if isinstance(item, dict)
                ]

            if isinstance(value, dict):
                return [
                    item
                    for item in value.values()
                    if isinstance(item, dict)
                ]

        return []


def parse_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()

        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def number(value):
    try:
        result = float(value)

        if result != result:
            return None

        if result in (
            float("inf"),
            float("-inf"),
        ):
            return None

        return result

    except (TypeError, ValueError):
        return None


def normalize_shift(raw):
    location = str(
        raw.get("bubo_contract_location_name")
        or raw.get("location")
        or raw.get("site")
        or "Unknown location"
    ).strip()

    start = (
        raw.get("start_timestamp")
        or raw.get("start")
        or raw.get("start_date")
    )

    end = (
        raw.get("end_timestamp")
        or raw.get("end")
        or raw.get("end_date")
    )

    start_at = parse_datetime(start)
    end_at = parse_datetime(end)

    if start_at and end_at:
        hours = (
            end_at - start_at
        ).total_seconds() / 3600
    else:
        hours = 0

    shift_id = (
        raw.get("bubo_shift_id")
        or raw.get("shift_id")
        or raw.get("id")
    )

    if not shift_id:
        shift_id = f"{location}-{start}-{end}"

    return {
        "shyftr_id": str(shift_id),
        "site": location,
        "start_at": start_at,
        "end_at": end_at,
        "shift_date": (
            start_at.date()
            if start_at
            else None
        ),
        "start_time": (
            start_at.timetz().replace(tzinfo=None)
            if start_at
            else None
        ),
        "end_time": (
            end_at.timetz().replace(tzinfo=None)
            if end_at
            else None
        ),
        "hours": max(hours, 0),
        "shift_type": str(
            raw.get("schedule_type")
            or raw.get("shift_type")
            or raw.get("type")
            or ""
        ),
        "value": number(
            raw.get("estimated_total_pay")
            or raw.get("value")
            or raw.get("pay")
        ),
        "distance": number(
            raw.get("distance")
        ),
        "autoassignable": bool(
            raw.get("is_autoassignable")
            or raw.get("autoassignable")
        ),
        "status": str(
            raw.get("status")
            or "Available"
        ),
        "raw_data": raw,
    }


def normalize_shifts(raw_shifts):
    return [
        normalize_shift(raw)
        for raw in raw_shifts
    ]
