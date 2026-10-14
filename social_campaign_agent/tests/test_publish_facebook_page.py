import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_facebook_page import (
    ASSETS_ROOT,
    MAX_STATUS_CHECKS,
    PublicationError,
    _status_ready,
    publish_page_post,
)


class FacebookPagePublishTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=ASSETS_ROOT)
        self.asset_dir = Path(self.tempdir.name)
        self.photo = self.asset_dir / "poster.png"
        self.photo.write_bytes(b"test-png-bytes")
        self.video = self.asset_dir / "reel.mp4"
        self.video.write_bytes(b"test-mp4-bytes")
        self.caption = self.asset_dir / "caption.txt"
        self.caption.write_text("Verified optogenetics caption with sources.", encoding="utf-8")
        self.calls = []
        self.responses = []

    def tearDown(self):
        self.tempdir.cleanup()

    def transport(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return 200, json.dumps(response).encode("utf-8")

    @staticmethod
    def valid_token_debug():
        return {
            "data": {
                "is_valid": True,
                "scopes": ["pages_show_list", "pages_read_engagement", "pages_manage_posts"],
                "granular_scopes": [
                    {"scope": "pages_manage_posts", "target_ids": ["61595341701921"]}
                ],
            }
        }

    def publish(self, kind, approval="PUBLISH", transport=None):
        if not self.responses or not isinstance(self.responses[0], dict) or "data" not in self.responses[0]:
            self.responses.insert(0, self.valid_token_debug())
        return publish_page_post(
            approval,
            kind,
            "61595341701921",
            "CHILD & HOPE",
            self.photo if kind == "photo" else self.video,
            self.caption,
            token="secret-token-test",
            app_access_token="secret-app-token-test",
            graph_version="v26.0",
            transport=transport or self.transport,
            output=lambda _: None,
            sleep=lambda _: None,
        )

    def test_no_preview_makes_no_network_request(self):
        self.assertIsNone(self.publish("photo", approval="NO"))
        self.assertEqual(self.calls, [])

    def test_invalid_approval_makes_no_network_request(self):
        with self.assertRaisesRegex(PublicationError, "exactly NO, VERIFY, or PUBLISH"):
            self.publish("photo", approval="yes")
        self.assertEqual(self.calls, [])

    def test_verify_checks_page_identity_without_uploading(self):
        self.responses = [{"id": "61595341701921", "name": "CHILD & HOPE"}]
        self.assertIsNone(self.publish("reel", approval="VERIFY"))
        self.assertEqual([call[0] for call in self.calls], ["GET", "GET"])
        self.assertIn("/debug_token?", self.calls[0][1])
        self.assertIn("/me?fields=id,name", self.calls[1][1])
        self.assertFalse(any("video_reels" in call[1] or "/photos" in call[1] for call in self.calls))

    def test_verify_rejects_missing_page_publish_permission_without_identity_or_upload(self):
        self.responses = [{"data": {"is_valid": True, "scopes": ["pages_show_list", "pages_read_engagement"]}}]
        with self.assertRaisesRegex(PublicationError, "lacks required permissions: pages_manage_posts"):
            self.publish("reel", approval="VERIFY")
        self.assertEqual(len(self.calls), 1)
        self.assertIn("/debug_token?", self.calls[0][1])

    def test_verify_rejects_publish_permission_not_granted_for_expected_page(self):
        self.responses = [{
            "data": {
                "is_valid": True,
                "scopes": ["pages_show_list", "pages_read_engagement", "pages_manage_posts"],
                "granular_scopes": [{"scope": "pages_manage_posts", "target_ids": ["999"]}],
            }
        }]
        with self.assertRaisesRegex(PublicationError, "not granted for the approved Facebook Page ID"):
            self.publish("reel", approval="VERIFY")
        self.assertEqual(len(self.calls), 1)

    def test_oauth_error_reports_safe_code_and_subcode_without_token(self):
        output = []

        def rejected_token(method, url, headers, body, timeout):
            self.calls.append((method, url, headers, body, timeout))
            self.assertEqual(headers["Authorization"], "Bearer secret-app-token-test")
            return 401, json.dumps({
                "error": {
                    "type": "OAuthException",
                    "code": 190,
                    "error_subcode": 463,
                    "message": "private provider response",
                }
            }).encode()

        with self.assertRaisesRegex(PublicationError, "HTTP 401; OAuthException; code 190; subcode 463") as raised:
            self.publish("photo", approval="VERIFY", transport=rejected_token)
        self.assertNotIn("secret-token-test", str(raised.exception))
        self.assertNotIn("secret-app-token-test", str(raised.exception))
        self.assertNotIn("private provider response", str(raised.exception))
        self.assertIn("FB_APP_ACCESS_TOKEN", str(raised.exception))
        self.assertNotIn("FB_PAGE_ACCESS_TOKEN", str(raised.exception))
        self.assertEqual(len(self.calls), 1)

    def test_invalid_page_token_stops_before_identity_or_upload(self):
        self.responses = [{"data": {"is_valid": False}}]
        with self.assertRaisesRegex(PublicationError, "FB_PAGE_ACCESS_TOKEN is invalid or expired"):
            self.publish("reel", approval="VERIFY")
        self.assertEqual(len(self.calls), 1)

    def test_page_identity_oauth_failure_identifies_page_secret_without_upload(self):
        def rejected_page_token(method, url, headers, body, timeout):
            self.calls.append((method, url, headers, body, timeout))
            if len(self.calls) == 1:
                return 200, json.dumps(self.valid_token_debug()).encode()
            return 401, json.dumps({
                "error": {"type": "OAuthException", "code": 190, "message": "private provider response"}
            }).encode()

        with self.assertRaisesRegex(PublicationError, "Meta rejected FB_PAGE_ACCESS_TOKEN") as raised:
            self.publish("photo", transport=rejected_page_token)
        self.assertNotIn("FB_APP_ACCESS_TOKEN", str(raised.exception))
        self.assertNotIn("secret-token-test", str(raised.exception))
        self.assertNotIn("secret-app-token-test", str(raised.exception))
        self.assertNotIn("private provider response", str(raised.exception))
        self.assertEqual([call[0] for call in self.calls], ["GET", "GET"])

    def test_wrong_page_id_stops_before_upload(self):
        self.responses = [{"id": "1345909531941708", "name": "CHILD & HOPE"}]
        with self.assertRaisesRegex(PublicationError, "Page ID does not match"):
            self.publish("photo")
        self.assertEqual(len(self.calls), 2)

    def test_wrong_page_name_stops_before_upload(self):
        self.responses = [{"id": "61595341701921", "name": "Different Page"}]
        with self.assertRaisesRegex(PublicationError, "Page name does not match"):
            self.publish("photo")
        self.assertEqual(len(self.calls), 2)

    def test_photo_upload_is_multipart_and_returns_confirmed_post_id(self):
        self.responses = [
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"id": "123", "post_id": "61595341701921_456"},
        ]
        result = self.publish("photo")
        self.assertEqual(result, "61595341701921_456")
        self.assertEqual([call[0] for call in self.calls], ["GET", "GET", "POST"])
        self.assertTrue(self.calls[2][1].endswith("/61595341701921/photos"))
        self.assertEqual(self.calls[2][2]["Authorization"], "Bearer secret-token-test")
        self.assertTrue(self.calls[2][2]["Content-Type"].startswith("multipart/form-data; boundary="))
        self.assertIn(b"Verified optogenetics caption with sources.", self.calls[2][3])
        self.assertIn(b"test-png-bytes", self.calls[2][3])

    def test_reel_follows_start_upload_ready_finish_sequence(self):
        upload_url = "https://rupload.facebook.com/video-upload/v26.0/903"
        self.responses = [
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"video_id": "903", "upload_url": upload_url},
            {"success": True},
            {"status": {
                "video_status": "ready",
                "uploading_phase": {"status": "complete"},
                "processing_phase": {"status": "complete"},
            }},
            {"success": True},
        ]
        result = self.publish("reel")
        self.assertEqual(result, "903")
        self.assertEqual([call[0] for call in self.calls], ["GET", "GET", "POST", "POST", "GET", "POST"])
        self.assertEqual(self.calls[3][1], upload_url)
        self.assertEqual(self.calls[3][2]["Authorization"], "OAuth secret-token-test")
        self.assertEqual(self.calls[3][2]["offset"], "0")
        self.assertEqual(self.calls[3][2]["file_size"], str(len(b"test-mp4-bytes")))
        self.assertIn(b"video_state=PUBLISHED", self.calls[5][3])

    def test_untrusted_upload_host_stops_before_video_upload(self):
        self.responses = [
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"video_id": "903", "upload_url": "https://attacker.example/upload/903"},
        ]
        with self.assertRaisesRegex(PublicationError, "unsafe or unexpected"):
            self.publish("reel")
        self.assertEqual(len(self.calls), 3)

    def test_reel_processing_error_never_calls_finish(self):
        self.responses = [
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"video_id": "903", "upload_url": "https://rupload.facebook.com/video-upload/v26.0/903"},
            {"success": True},
            {"status": {
                "video_status": "processing",
                "uploading_phase": {"status": "complete"},
                "processing_phase": {"status": "error"},
            }},
        ]
        with self.assertRaisesRegex(PublicationError, "processing failed"):
            self.publish("reel")
        self.assertFalse(any(call[1].endswith("/video_reels") for call in self.calls[4:]))

    def test_upload_complete_but_processing_in_progress_is_not_ready(self):
        self.assertFalse(_status_ready({"status": {
            "video_status": "upload_complete",
            "uploading_phase": {"status": "complete"},
            "processing_phase": {"status": "in_progress"},
        }}))

    def test_reel_bounded_wait_never_calls_finish(self):
        self.responses = [
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"video_id": "903", "upload_url": "https://rupload.facebook.com/video-upload/v26.0/903"},
            {"success": True},
        ] + [{"status": {
            "video_status": "processing",
            "uploading_phase": {"status": "complete"},
            "processing_phase": {"status": "in_progress"},
        }} for _ in range(MAX_STATUS_CHECKS)]
        with self.assertRaisesRegex(PublicationError, "bounded wait"):
            self.publish("reel")
        self.assertEqual(len(self.calls), 4 + MAX_STATUS_CHECKS)

    def test_token_is_not_printed(self):
        self.responses = [
            self.valid_token_debug(),
            {"id": "61595341701921", "name": "CHILD & HOPE"},
            {"id": "123", "post_id": "61595341701921_456"},
        ]
        lines = []
        publish_page_post(
            "PUBLISH", "photo", "61595341701921", "CHILD & HOPE", self.photo,
            self.caption, token="secret-token-test", app_access_token="secret-app-token-test", graph_version="v26.0",
            transport=self.transport, output=lines.append,
        )
        self.assertNotIn("secret-token-test", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()