import json
import os
import threading
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE = {"access": "", "refresh": ""}


class ShyftrError(Exception):
    """Raised when the Shyftr API cannot be reached or understood."""


class ShyftrClient:
    CLIENT_ID = "5a1kunab6mms590v4eh4fslj5i"
    TOKEN_ENDPOINT = "https://api.bubo.io/auth/token"

    @staticmethod
    def _read_env(*names, default=""):
        for name in names:
            value = os.getenv(name)
            if value is not None and str(value).strip():
                return str(value).strip()
        return default

    def __init__(self):
        # Refresh tokens are often rotated. Keep the newest pair in memory so a
        # new request does not keep reusing the now-invalid token from .env.
        with _TOKEN_LOCK:
            self.token = _TOKEN_CACHE["access"] or self._read_env(
                "SHYFTR_ACCESS_TOKEN",
            )
            self.refresh_token = _TOKEN_CACHE["refresh"] or self._read_env(
                "SHYFTR_REFRESH_TOKEN",
                "SHYFTR_REFRESH",
            )

        self.endpoint = os.getenv(
            "SHYFTR_SHIFT_ENDPOINT",
            "https://api.bubo.io/shyftr/shift",
        )

        self.timeout = int(
            os.getenv("SHYFTR_TIMEOUT", "15")
        )

    def refresh_access_token(self):
        if not self.refresh_token:
            raise ShyftrError(
                "SHYFTR_REFRESH_TOKEN is not configured."
            )

        body = json.dumps(
            {
                "grant_type": "refresh_token",
                "client_id": self.CLIENT_ID,
                "refresh_token": self.refresh_token,
            }
        ).encode("utf-8")

        request = Request(
            self.TOKEN_ENDPOINT,
            data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://shyftr.bubo.io",
            "Referer": "https://shyftr.bubo.io/",
        },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as error:
            error_body = error.read().decode(
                "utf-8",
                errors="replace",
            )

            raise ShyftrError(
                f"Shyftr token refresh failed "
                f"(HTTP {error.code}): {error_body}"
            ) from error

        except URLError as error:
            raise ShyftrError(
                "Unable to reach Shyftr authentication service."
            ) from error

        except json.JSONDecodeError as error:
            raise ShyftrError(
                "Shyftr authentication returned invalid JSON."
            ) from error

        # The API has returned both PascalCase and OAuth-standard snake_case
        # fields across versions.
        access_token = str(
            payload.get("AccessToken")
            or payload.get("access_token")
            or payload.get("token")
            or ""
        ).strip()

        new_refresh_token = str(
            payload.get("RefreshToken")
            or payload.get("refresh_token")
            or ""
        ).strip()

        if not access_token:
            raise ShyftrError(
                "Shyftr authentication did not return "
                "an AccessToken."
            )

        self.token = access_token

        if new_refresh_token:
            self.refresh_token = new_refresh_token

        with _TOKEN_LOCK:
            _TOKEN_CACHE["access"] = self.token
            _TOKEN_CACHE["refresh"] = self.refresh_token

        return payload

    def fetch_shifts(self):
        if not self.token:
            raise ShyftrError(
                "SHYFTR_ACCESS_TOKEN is not configured."
            )

        try:
            return self._request_shifts()

        except ShyftrError as error:
            if "401" in str(error) or "403" in str(error):
                raise ShyftrError(
                    "Shyftr access token has expired or is no longer valid. "
                    "Update SHYFTR_ACCESS_TOKEN."
                ) from error

            raise

    def _request_shifts(self):
        credential = (
            self.token
            .removeprefix("Bearer ")
            .removeprefix("bearer ")
        )

        request = Request(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {credential}",
                "Accept": (
                    "application/json, "
                    "text/plain, */*"
                ),
                "User-Agent": "Mozilla/5.0",
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as error:
            if error.code in (401, 403):
                raise ShyftrError(
                    f"Shyftr returned {error.code}."
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
