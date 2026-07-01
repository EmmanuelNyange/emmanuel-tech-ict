import unittest

from python_backend import build_confirmation_link, get_confirmation_channel


class ConfirmationTests(unittest.TestCase):
    def test_prefers_whatsapp_when_requested(self):
        channel = get_confirmation_channel("0716205974", "whatsapp")
        self.assertEqual(channel, "whatsapp")

    def test_falls_back_to_email_for_email_contacts(self):
        channel = get_confirmation_channel("client@example.com", "")
        self.assertEqual(channel, "email")

    def test_builds_whatsapp_link_with_ticket_details(self):
        booking = {
            "name": "Jane Doe",
            "ticket_code": "TKT-123",
            "service": "Computer Repair",
            "service_datetime": "2026-07-02 10:00",
            "description": "Laptop screen issue",
        }
        link = build_confirmation_link("0716205974", booking, "whatsapp")
        self.assertIn("wa.me", link)
        self.assertIn("TKT-123", link)


if __name__ == "__main__":
    unittest.main()
