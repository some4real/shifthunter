from pathlib import Path

from django.template.loader import render_to_string
from django.test import SimpleTestCase


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
