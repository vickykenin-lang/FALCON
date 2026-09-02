import unittest

from interface.telegram import TelegramConfig, TelegramGateway


class Heartbeat:
    def to_dict(self):
        return {"payload": {"status": "HEALTHY"}}


class Mission:
    def __init__(self, objective):
        self.mission_id = "m1"
        self.objective = objective
        self.status = "DISCOVERING"
        self.attempts = 0


class Driver:
    def run(self, mission, context=None):
        mission.status = "SUCCEEDED"
        self.context = context
        return mission


class Runtime:
    def __init__(self):
        self.driver = Driver()
        self.accepted = []

    def heartbeat(self):
        return Heartbeat()

    def accept(self, objective, **kwargs):
        self.accepted.append((objective, kwargs))
        return Mission(objective)


class FakeClient:
    def __init__(self):
        self.sent = []

    def get_me(self):
        return {"username": "falcon_optimus_bot"}

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return {"message_id": 1}


class TelegramGatewayTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.client = FakeClient()
        self.gateway = TelegramGateway(
            self.runtime,
            TelegramConfig(bot_token="test-token", allowed_user_id=42),
            client=self.client,
        )

    def update(self, user_id=42, text="hello"):
        return {
            "update_id": 1,
            "message": {
                "from": {"id": user_id},
                "chat": {"id": 1001},
                "text": text,
            },
        }

    def test_verifies_expected_bot_identity_from_telegram(self):
        self.assertEqual(self.gateway.verify_bot()["username"], "falcon_optimus_bot")

    def test_rejects_non_founder_user(self):
        result = self.gateway.process_update(self.update(user_id=99, text="do work"))
        self.assertEqual(result, "denied")
        self.assertEqual(self.runtime.accepted, [])
        self.assertIn("access denied", self.client.sent[-1][1].lower())

    def test_health_command(self):
        result = self.gateway.process_update(self.update(text="/health"))
        self.assertEqual(result, "health")
        self.assertIn("HEALTHY", self.client.sent[-1][1])

    def test_plain_text_becomes_founder_mission(self):
        result = self.gateway.process_update(self.update(text="Inspect the assigned project"))
        self.assertEqual(result, "mission")
        objective, kwargs = self.runtime.accepted[-1]
        self.assertEqual(objective, "Inspect the assigned project")
        self.assertEqual(kwargs["context"]["channel"], "telegram")
        self.assertEqual(kwargs["context"]["founder_user_id"], 42)
        self.assertIn("SUCCEEDED", self.client.sent[-1][1])


if __name__ == "__main__":
    unittest.main()
