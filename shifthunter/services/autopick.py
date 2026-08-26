from dataclasses import dataclass


@dataclass
class AutoPickResult:
    attempted: bool
    success: bool
    message: str


class AutoPickService:
    """
    Handles automatic shift claiming.

    The actual Shyftr claim endpoint is intentionally not implemented yet.
    No fake/simulated claim is performed.
    """

    def claim_shift(self, shift):
        return AutoPickResult(
            attempted=False,
            success=False,
            message=(
                "Auto-Pick is enabled, but the Shyftr claim "
                "endpoint is not configured yet."
            ),
        )
