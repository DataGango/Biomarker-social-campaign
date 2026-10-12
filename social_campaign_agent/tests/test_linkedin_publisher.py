import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from linkedin_publisher import LinkedInConfig, LinkedInPublisher, _read_image


class FakeResponse:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


class LinkedInPublisherTests(unittest.TestCase):
    def setUp(self):
        self.requests = []

        def opener(request, timeout):
            self.requests.append((request, timeout))
            if request.full_url.endswith("initializeUpload"):
                return FakeResponse(200, body=json.dumps({"value": {
                    "uploadUrl": "https://www.linkedin.com/dms-uploads/upload-id",
                    "image": "urn:li:image:image-id",
                }}).encode())
            if request.full_url == "https://www.linkedin.com/dms-uploads/upload-id":
                return FakeResponse(201)
            return FakeResponse(201, {"x-restli-id": "urn:li:share:12345"})

        self.config = LinkedInConfig("test-token", "urn:li:person:123", "202609")
        self.publisher = LinkedInPublisher(self.config, opener=opener)

    def test_config_reads_local_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "LINKEDIN_ACCESS_TOKEN='file-token'\n"
                "LINKEDIN_AUTHOR_URN=urn:li:person:file-id\n"
                "LINKEDIN_VERSION=202608\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = LinkedInConfig.from_env(env_file)

        self.assertEqual(config.access_token, "file-token")
        self.assertEqual(config.author_urn, "urn:li:person:file-id")
        self.assertEqual(config.api_version, "202608")

    def test_environment_values_override_local_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "LINKEDIN_ACCESS_TOKEN=file-token\n"
                "LINKEDIN_AUTHOR_URN=urn:li:person:file-id\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {
                "LINKEDIN_ACCESS_TOKEN": "shell-token",
                "LINKEDIN_AUTHOR_URN": "urn:li:person:shell-id",
            }, clear=True):
                config = LinkedInConfig.from_env(env_file)

        self.assertEqual(config.access_token, "shell-token")
        self.assertEqual(config.author_urn, "urn:li:person:shell-id")

    def test_requires_explicit_approval_before_network_request(self):
        with self.assertRaises(PermissionError):
            self.publisher.publish("Approved wording", approved=False)
        self.assertEqual(self.requests, [])

    def test_publishes_public_member_text_post_and_returns_confirmed_url(self):
        result = self.publisher.publish("Approved wording", approved=True)
        request = self.requests[0][0]
        payload = json.loads(request.data)

        self.assertEqual(request.full_url, "https://api.linkedin.com/rest/posts")
        self.assertEqual(request.get_header("Linkedin-version"), "202609")
        self.assertEqual(request.get_header("X-restli-protocol-version"), "2.0.0")
        self.assertEqual(payload["author"], "urn:li:person:123")
        self.assertEqual(payload["visibility"], "PUBLIC")
        self.assertEqual(payload["commentary"], "Approved wording")
        self.assertEqual(result["post_urn"], "urn:li:share:12345")
        self.assertIn("urn:li:share:12345", result["url"])

    def test_resolves_member_urn_from_linkedin_userinfo_when_not_configured(self):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            return FakeResponse(200, body=json.dumps({"sub": "member-oidc-id"}).encode())

        publisher = LinkedInPublisher(LinkedInConfig("test-token", ""), opener=opener)
        result = publisher.resolve_author_urn()

        self.assertEqual(result, "urn:li:person:member-oidc-id")
        self.assertEqual(requests[0].full_url, "https://api.linkedin.com/v2/userinfo")

    def test_invalid_configured_urn_falls_back_to_authenticated_userinfo(self):
        def opener(request, timeout):
            return FakeResponse(200, body=json.dumps({"sub": "member-oidc-id"}).encode())

        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "LINKEDIN_ACCESS_TOKEN=test-token\n"
                "LINKEDIN_AUTHOR_URN=https://www.linkedin.com/in/vanity\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = LinkedInConfig.from_env(env_file)
        publisher = LinkedInPublisher(config, opener=opener)

        self.assertEqual(publisher.resolve_author_urn(), "urn:li:person:member-oidc-id")

    def test_uploads_image_then_creates_post_with_alt_text(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "poster.png"
            image.write_bytes(b"png-data")
            result = self.publisher.publish(
                "Caption", image_path=image, alt_text="Poster description", approved=True
            )

        self.assertEqual([request.method for request, _ in self.requests], ["POST", "PUT", "POST"])
        self.assertEqual(self.requests[1][0].data, b"png-data")
        post = json.loads(self.requests[2][0].data)
        self.assertEqual(post["content"]["media"], {
            "id": "urn:li:image:image-id",
            "altText": "Poster description",
        })
        self.assertEqual(result["visibility"], "PUBLIC")

    def test_rejects_unsupported_media_type_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "poster.webp"
            image.write_bytes(b"image")
            with self.assertRaises(ValueError):
                self.publisher.publish("Caption", image_path=image, approved=True)
        self.assertEqual(self.requests, [])

    def test_rasterizes_svg_poster_to_png(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "poster.svg"
            image.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><circle cx="4" cy="4" r="3"/></svg>',
                encoding="utf-8",
            )
            image_data, mime_type = _read_image(image)

        self.assertEqual(mime_type, "image/png")
        self.assertTrue(image_data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_rejects_untrusted_image_upload_host(self):
        def malicious_opener(_request, _timeout):
            return FakeResponse(200, body=json.dumps({"value": {
                "uploadUrl": "https://attacker.example/upload",
                "image": "urn:li:image:image-id",
            }}).encode())

        publisher = LinkedInPublisher(self.config, opener=malicious_opener)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "poster.png"
            image.write_bytes(b"png-data")
            with self.assertRaises(Exception):
                publisher.publish("Caption", image_path=image, approved=True)


if __name__ == "__main__":
    unittest.main()