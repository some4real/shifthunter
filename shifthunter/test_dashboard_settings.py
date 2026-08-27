import os
from pathlib import Path
from unittest import mock

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from shifthunter.services.shyftr import ShyftrClient


class DashboardSettingsStylesTest(SimpleTestCase):
    def test_dashboard_includes_settings_drawer_and_styles(self):
        html = render_to_string("shifthunter/dashboard.html", {})

        self.assertIn('id="settingsOverlay"', html)
        self.assertIn('id="saveSettings"', html)

        css_path = (
            Path(__file__).resolve().parent
            / "static"
            / "shifthunter"
            / "dashboard.css"
        )
        css = css_path.read_text()

        self.assertIn(".settings-overlay", css)
        self.assertIn(".settings-panel", css)
        self.assertIn(".settings-section", css)

    @mock.patch.dict(
        os.environ,
        {
            "SHYFTR_ACCESS_TOKEN": "abc123",
            "SHYFTR_REFRESH_TOKEN": "refresh456",
        },
        clear=True,
    )
    def test_shyftr_client_reads_access_token_alias(self):
        client = ShyftrClient()

        self.assertEqual(client.token, "abc123")
        self.assertEqual(client.refresh_token, "refresh456")

    @mock.patch("shifthunter.services.shyftr.urlopen")
    def test_refresh_access_token_uses_oauth_form_encoding(self, mock_urlopen):
        mock_response = mock.MagicMock()
        mock_response.__enter__.return_value = mock_response
        mock_response.read.return_value = (
            b'{"AccessToken": "new-access", "RefreshToken": "new-refresh"}'
        )
        mock_urlopen.return_value = mock_response

        with mock.patch.dict(
            os.environ,
            {"SHYFTR_REFRESH_TOKEN": "old-refresh"},
            clear=True,
        ):
            client = ShyftrClient()
            payload = client.refresh_access_token()

        self.assertEqual(payload["AccessToken"], "new-access")
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.get_header("Content-type"),
            "application/x-www-form-urlencoded",
        )
        self.assertIn("grant_type=refresh_token", request.data.decode("utf-8"))
        self.assertIn("client_id=5a1kunab6mms590v4eh4fslj5i", request.data.decode("utf-8"))
        self.assertIn("refresh_token=old-refresh", request.data.decode("utf-8"))
