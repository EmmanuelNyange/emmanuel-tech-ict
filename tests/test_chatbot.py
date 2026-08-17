import unittest
from unittest.mock import patch

from python_backend import app, get_chatbot_fallback_reply, get_chatbot_provider, is_valid_contact


class ChatbotTests(unittest.TestCase):
    def test_booking_message_returns_booking_guidance(self):
        reply = get_chatbot_fallback_reply("I want to book a service")
        self.assertIn("book", reply.lower())

    def test_contact_message_returns_contact_details(self):
        reply = get_chatbot_fallback_reply("How can I contact you")
        self.assertIn("0716205974", reply)

    def test_greeting_message_returns_salutation(self):
        reply = get_chatbot_fallback_reply("Hello there")
        self.assertIn("hello", reply.lower())
        self.assertIn("e-tech", reply.lower())

    def test_thank_you_message_returns_polite_reply(self):
        reply = get_chatbot_fallback_reply("Thank you so much")
        self.assertIn("welcome", reply.lower())

    def test_chatbot_booking_intent_returns_booking_guidance(self):
        reply = get_chatbot_fallback_reply("Book me for laptop repair tomorrow at 10am")
        self.assertIn("book", reply.lower())

    def test_chatbot_provider_detects_gemini_key(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "real-gemini-key-1234567890"}, clear=False):
            self.assertEqual(get_chatbot_provider(), "gemini")

    def test_valid_contact_accepts_phone_and_email(self):
        self.assertTrue(is_valid_contact("0716205974"))
        self.assertTrue(is_valid_contact("user@example.com"))
        self.assertFalse(is_valid_contact("not-a-valid-contact"))

    def test_chatbot_route_returns_json_reply(self):
        client = app.test_client()
        response = client.post("/chatbot", json={"message": "I want to book a service"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)


if __name__ == "__main__":
    unittest.main()
