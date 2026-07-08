import unittest

from python_backend import app, get_chatbot_fallback_reply


class ChatbotTests(unittest.TestCase):
    def test_booking_message_returns_booking_guidance(self):
        reply = get_chatbot_fallback_reply("I want to book a service")
        self.assertIn("book", reply.lower())

    def test_contact_message_returns_contact_details(self):
        reply = get_chatbot_fallback_reply("How can I contact you")
        self.assertIn("0716205974", reply)

    def test_chatbot_route_returns_json_reply(self):
        client = app.test_client()
        response = client.post("/chatbot", json={"message": "I want to book a service"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)


if __name__ == "__main__":
    unittest.main()
