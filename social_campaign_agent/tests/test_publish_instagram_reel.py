import unittest
from pathlib import Path

from scripts.publish_instagram import Config, PublicationError, MAX_STATUS_CHECKS
from scripts.publish_instagram_reel import publish_reel, validate_video_url


class ReelTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.lines = []
        self.waits = []
        self.responses = [
            {"user_id": "123", "username": "gangopadhyay.poulomi"},
            {"id": "456"}, {"status_code": "FINISHED"}, {"id": "789"},
            {"id": "789", "permalink": "https://www.instagram.com/reel/approvedV2/", "media_product_type": "REELS"},
        ]

    def transport(self, method, url, headers, data, timeout):
        import json
        self.calls.append((method, url, data))
        return 200, json.dumps(self.responses.pop(0)).encode()

    def publish(self, approval="PUBLISH", transport=None):
        return publish_reel(Config("do-not-log-token", "v26.0", ""), approval,
                            "gangopadhyay.poulomi", "https://cdn.example.org/v2.mp4",
                            Path("assets/durga-pujo-v2-caption.txt"),
                            transport=transport or self.transport,
                            output=self.lines.append, sleep=self.waits.append)

    def test_reels_payload_and_exact_caption(self):
        self.assertEqual(self.publish(), "789")
        payload = self.calls[1][2]
        self.assertEqual(payload["media_type"], "REELS")
        self.assertEqual(payload["video_url"], "https://cdn.example.org/v2.mp4")
        self.assertNotIn("image_url", payload)
        self.assertEqual(payload["caption"], (Path(__file__).resolve().parents[1] / "assets/durga-pujo-v2-caption.txt").read_text().strip())
        self.assertEqual(self.calls[3][2], {"creation_id": "456"})
        self.assertIn("Instagram permalink: https://www.instagram.com/reel/approvedV2/", self.lines)

    def test_preview_no_network(self):
        self.assertIsNone(self.publish("NO"))
        self.assertEqual(self.calls, [])

    def test_username_mismatch(self):
        self.responses[0]["username"] = "wrong.account"
        with self.assertRaisesRegex(PublicationError, "does not match"):
            self.publish()
        self.assertEqual(len(self.calls), 1)

    def test_only_finished_can_publish(self):
        for state in ("ERROR", "EXPIRED", "PUBLISHED", "UNKNOWN"):
            with self.subTest(state=state):
                self.setUp()
                self.responses[2]["status_code"] = state
                with self.assertRaisesRegex(PublicationError, "not FINISHED"):
                    self.publish()
                self.assertFalse(any(url.endswith("/media_publish") for _, url, _ in self.calls))

    def test_bounded_processing_timeout(self):
        self.responses = self.responses[:2] + [{"status_code": "IN_PROGRESS"}] * MAX_STATUS_CHECKS
        with self.assertRaisesRegex(PublicationError, "bounded wait"):
            self.publish()
        self.assertEqual(len(self.waits), MAX_STATUS_CHECKS - 1)
        self.assertFalse(any(url.endswith("/media_publish") for _, url, _ in self.calls))

    def test_token_redaction(self):
        def failing_transport(*args):
            raise RuntimeError("do-not-log-token")
        with self.assertRaises(PublicationError) as raised:
            self.publish(transport=failing_transport)
        self.assertNotIn("do-not-log-token", str(raised.exception) + "\n".join(self.lines))

    def test_api_error_redaction(self):
        with self.assertRaises(PublicationError) as raised:
            self.publish(transport=lambda *args: (400, b'{"error":{"message":"do-not-log-token"}}'))
        self.assertNotIn("do-not-log-token", str(raised.exception))

    def test_rejects_unsafe_video_urls(self):
        for url in ("http://cdn.example.org/v.mp4", "https://localhost/v.mp4",
                    "https://127.0.0.1/v.mp4", "https://cdn.example.org/v.jpg",
                    "https://user:password@cdn.example.org/v.mp4", "https://cdn.example.org/v.mp4?token=x"):
            with self.subTest(url=url), self.assertRaises(PublicationError):
                validate_video_url(url)