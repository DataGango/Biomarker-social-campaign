import io
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from scripts.publish_instagram import (
    Config,
    PublicationError,
    publish_post,
    resolve_campaign_file,
    validate_image_url,
)


VALID_CONFIG = Config(
    account_id="123456789012345",
    access_token="test-token-do-not-log",
    graph_api_version="v25.0",
    image_url="https://cdn.example.org/climate-poster.jpg",
)


class PublishInstagramTests(unittest.TestCase):
    def test_config_requires_access_token_but_not_separate_account_id(self):
        with patch.dict(
            "os.environ",
            {
                "IG_ACCESS_TOKEN": "test-token",
                "IG_GRAPH_API_VERSION": "v26.0",
                "IG_IMAGE_URL": "https://cdn.example.org/climate-poster.jpg",
            },
            clear=True,
        ):
            from scripts.publish_instagram import config_from_environment

            config = config_from_environment()

        self.assertIsNone(config.account_id)
        self.assertEqual(config.access_token, "test-token")

    def test_account_profile_must_match_target_alias_before_upload(self):
        calls = []

        def transport(method, url, headers, data, timeout):
            calls.append((method, url, data))
            return 200, b'{"user_id":"123456789012345","username":"different.account"}'

        with self.assertRaisesRegex(PublicationError, "does not match the approved target alias"):
            publish_post(
                VALID_CONFIG,
                "PUBLISH",
                "Climate campaign account",
                transport=transport,
                output=lambda _: None,
            )

        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1].endswith("/me?fields=user_id,username"))

    def test_missing_approval_previews_without_network(self):
        calls = []
        lines = []

        result = publish_post(
            VALID_CONFIG,
            None,
            "Climate campaign account",
            transport=lambda *args: calls.append(args),
            output=lines.append,
        )

        self.assertIsNone(result)
        self.assertEqual(calls, [])
        preview = "\n".join(lines)
        self.assertIn("Target account alias: Climate campaign account", preview)
        self.assertIn("Poster asset: assets/climate-change-instagram-poster.jpg", preview)
        self.assertIn("Public image URL: https://cdn.example.org/climate-poster.jpg", preview)
        self.assertIn("Human activities, especially burning fossil fuels", preview)
        self.assertIn("Alt text handoff (not sent through the publishing API)", preview)
        self.assertIn("A dark green poster", preview)
        self.assertIn("No network requests were made", preview)

    def test_preview_without_public_url_is_explicitly_non_publishable(self):
        lines = []

        result = publish_post(
            None,
            "NO",
            "Climate campaign account",
            transport=lambda *args: self.fail("Preview must not make network requests"),
            output=lines.append,
            asset_path=Path("assets/climate-change-instagram-poster.jpg"),
        )

        self.assertIsNone(result)
        self.assertIn("Public image URL: NOT CONFIGURED (preview only; publishing is blocked)", lines)

    def test_campaign_files_must_be_supported_assets(self):
        with self.assertRaisesRegex(PublicationError, "inside the repository's assets"):
            resolve_campaign_file("tests/test_publish_instagram.py", {".jpg"}, "Poster asset")
        with self.assertRaisesRegex(PublicationError, "extensions"):
            resolve_campaign_file("assets/climate-change-instagram-poster.png", {".jpg", ".jpeg"}, "Poster asset")

    def test_invalid_approval_is_rejected_without_network(self):
        calls = []
        for approval in ("yes", " PUBLISH "):
            with self.subTest(approval=approval), self.assertRaisesRegex(
                PublicationError, "exactly NO or PUBLISH"
            ):
                publish_post(
                    VALID_CONFIG,
                    approval,
                    "Climate account",
                    transport=lambda *args: calls.append(args),
                    output=lambda _: None,
                )
        self.assertEqual(calls, [])

    def test_rejects_non_https_private_and_non_jpeg_urls(self):
        urls = (
            "http://cdn.example.org/poster.jpg",
            "https://localhost/poster.jpg",
            "https://127.0.0.1/poster.jpg",
            "https://cdn.example.org/poster.png",
            "https://user:pass@cdn.example.org/poster.jpg",
            "https://cdn.example.org/poster.jpg?token=secret",
        )
        for url in urls:
            with self.subTest(url=url), self.assertRaises(PublicationError):
                validate_image_url(url)

    def test_publishes_container_after_it_is_ready(self):
        calls = []
        responses = [
            (200, b'{"user_id":"123456789012345","username":"Climate campaign account"}'),
            (200, b'{"id":"container-1"}'),
            (200, b'{"status_code":"FINISHED"}'),
            (200, b'{"id":"media-1"}'),
        ]

        def transport(method, url, headers, data, timeout):
            calls.append((method, url, headers, data, timeout))
            return responses.pop(0)

        lines = []
        result = publish_post(
            VALID_CONFIG,
            "PUBLISH",
            "Climate campaign account",
            transport=transport,
            output=lines.append,
            sleep=lambda _: self.fail("A finished container should not wait"),
        )

        self.assertEqual(result, "media-1")
        self.assertEqual([call[0] for call in calls], ["GET", "POST", "GET", "POST"])
        self.assertTrue(calls[0][1].endswith("/me?fields=user_id,username"))
        self.assertTrue(calls[1][1].endswith("/123456789012345/media"))
        self.assertEqual(calls[1][3]["image_url"], VALID_CONFIG.image_url)
        self.assertIn("Human activities, especially burning fossil fuels", calls[1][3]["caption"])
        self.assertEqual(calls[3][3], {"creation_id": "container-1"})
        self.assertTrue(all(call[2]["Authorization"] == "Bearer test-token-do-not-log" for call in calls))
        self.assertNotIn(VALID_CONFIG.access_token, "\n".join(lines))
        self.assertIn("Published successfully. Instagram media ID: media-1", lines)

    def test_api_error_is_sanitized_and_stops_before_polling(self):
        calls = []

        def transport(*args):
            calls.append(args)
            return 400, b'{"error":{"message":"rejected; token=test-token-do-not-log"}}'

        error_output = io.StringIO()
        with redirect_stderr(error_output), self.assertRaises(PublicationError) as raised:
            publish_post(
                VALID_CONFIG,
                "PUBLISH",
                "Climate campaign account",
                transport=transport,
                output=lambda _: None,
            )

        self.assertEqual(len(calls), 1)
        self.assertIn("HTTP 400", str(raised.exception))
        self.assertNotIn(VALID_CONFIG.access_token, str(raised.exception) + error_output.getvalue())

    def test_container_failure_does_not_publish(self):
        calls = []
        responses = [
            (200, b'{"user_id":"123456789012345","username":"Climate campaign account"}'),
            (200, b'{"id":"container-1"}'),
            (200, b'{"status_code":"ERROR"}'),
        ]

        def transport(*args):
            calls.append(args)
            return responses.pop(0)

        with self.assertRaisesRegex(PublicationError, "status: ERROR"):
            publish_post(
                VALID_CONFIG,
                "PUBLISH",
                "Climate campaign account",
                transport=transport,
                output=lambda _: None,
                sleep=lambda _: None,
            )
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()