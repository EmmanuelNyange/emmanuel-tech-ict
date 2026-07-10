import unittest

from python_backend import app, build_mpesa_stk_payload, normalize_phone_number


class MpesaTests(unittest.TestCase):
    def test_normalize_phone_number_converts_local_format(self):
        self.assertEqual(normalize_phone_number("0716205974"), "254716205974")

    def test_build_mpesa_stk_payload_contains_expected_fields(self):
        payload = build_mpesa_stk_payload("254716205974", 1000, "TKT-123")
        self.assertEqual(payload["PhoneNumber"], "254716205974")
        self.assertEqual(payload["Amount"], 1000)
        self.assertIn("TKT-123", payload["AccountReference"])

    def test_payment_request_route_requires_authentication(self):
        client = app.test_client()
        response = client.post("/admin/bookings/1/payment-request", json={"phone": "0716205974", "amount": 1000})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
