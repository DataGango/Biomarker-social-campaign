"""Publish approved member posts through LinkedIn's official REST API."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


API_BASE = "https://api.linkedin.com/rest"
IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
}


class LinkedInPublishError(RuntimeError):
    pass


class LinkedInConfig:
    def __init__(self, access_token, author_urn, api_version="202609"):
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("LinkedIn access token is required.")
        if author_urn and (not isinstance(author_urn, str) or not author_urn.startswith("urn:li:person:")):
            raise ValueError("LINKEDIN_AUTHOR_URN must be blank or a member URN: urn:li:person:<id>.")
        if len(api_version) != 6 or not api_version.isdigit():
            raise ValueError("LinkedIn API version must use YYYYMM format.")
        self.access_token = access_token.strip()
        self.author_urn = author_urn.strip()
        self.api_version = api_version

    @classmethod
    def from_env(cls, env_path=None):
        file_values = _load_env_file(env_path or Path(__file__).with_name(".env"))
        author_urn = os.environ.get("LINKEDIN_AUTHOR_URN", file_values.get("LINKEDIN_AUTHOR_URN", ""))
        if author_urn and not author_urn.startswith("urn:li:person:"):
            author_urn = ""
        return cls(
            os.environ.get("LINKEDIN_ACCESS_TOKEN", file_values.get("LINKEDIN_ACCESS_TOKEN", "")),
            author_urn,
            os.environ.get("LINKEDIN_VERSION", file_values.get("LINKEDIN_VERSION", "202609")),
        )


class LinkedInPublisher:
    def __init__(self, config, opener=urlopen):
        self.config = config
        self.opener = opener

    def resolve_author_urn(self):
        if self.config.author_urn:
            return self.config.author_urn
        response = self._request(
            "GET",
            "https://api.linkedin.com/v2/userinfo",
            headers={"Accept": "application/json"},
        )
        try:
            subject = json.loads(response.body)["sub"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LinkedInPublishError(
                "LinkedIn userinfo did not return a member ID; authorize the app with openid and profile scopes."
            ) from exc
        if not isinstance(subject, str) or not subject.strip():
            raise LinkedInPublishError("LinkedIn userinfo returned an empty member ID.")
        self.config.author_urn = f"urn:li:person:{subject.strip()}"
        return self.config.author_urn

    def publish(self, commentary, image_path=None, alt_text="", approved=False):
        if approved is not True:
            raise PermissionError("Publishing requires explicit approval of this exact post.")
        if not isinstance(commentary, str) or not commentary.strip():
            raise ValueError("Post text must not be empty.")
        author_urn = self.resolve_author_urn()

        post = {
            "author": author_urn,
            "commentary": commentary.strip(),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if image_path is not None:
            image_data, mime_type = _read_image(image_path)
            image_urn = self._upload_image(image_data, mime_type)
            media = {"id": image_urn}
            if alt_text.strip():
                media["altText"] = alt_text.strip()
            post["content"] = {"media": media}

        response = self._request(
            "POST",
            f"{API_BASE}/posts",
            body=post,
            headers={"Content-Type": "application/json"},
        )
        post_urn = response.headers.get("x-restli-id") or response.headers.get("X-RestLi-Id")
        if response.status not in (200, 201) or not post_urn:
            raise LinkedInPublishError("LinkedIn did not confirm post creation.")
        return {
            "post_urn": post_urn,
            "url": f"https://www.linkedin.com/feed/update/{post_urn}/",
            "visibility": "PUBLIC",
            "author": author_urn,
        }

    def _upload_image(self, image_data, mime_type):
        response = self._request(
            "POST",
            f"{API_BASE}/images?action=initializeUpload",
            body={"initializeUploadRequest": {"owner": self.config.author_urn}},
            headers={"Content-Type": "application/json"},
        )
        try:
            value = json.loads(response.body)["value"]
            upload_url = value["uploadUrl"]
            image_urn = value["image"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LinkedInPublishError("LinkedIn returned an invalid image-upload response.") from exc

        upload_host = urlparse(upload_url)
        if upload_host.scheme != "https" or upload_host.hostname != "www.linkedin.com":
            raise LinkedInPublishError("LinkedIn returned an unexpected image upload host.")
        self._request(
            "PUT",
            upload_url,
            raw_body=image_data,
            headers={"Content-Type": mime_type},
        )
        return image_urn

    def _request(self, method, url, body=None, raw_body=None, headers=None):
        request_headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Linkedin-Version": self.config.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        request_headers.update(headers or {})
        data = raw_body if raw_body is not None else (
            json.dumps(body).encode("utf-8") if body is not None else None
        )
        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            with self.opener(request, timeout=45) as response:
                return _HttpResponse(response.status, response.headers, response.read())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            raise LinkedInPublishError(f"LinkedIn API returned HTTP {exc.code}: {detail or exc.reason}") from exc
        except URLError as exc:
            raise LinkedInPublishError(f"LinkedIn request failed: {exc.reason}") from exc


class _HttpResponse:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body


def _read_image(image_path):
    path = Path(image_path).expanduser()
    if not path.is_file():
        raise ValueError("Image file does not exist.")
    if path.suffix.lower() == ".svg":
        with tempfile.TemporaryDirectory(prefix="linkedin-image-") as directory:
            png_path = Path(directory) / "upload.png"
            try:
                subprocess.run(
                    ["sips", "-s", "format", "png", str(path), "--out", str(png_path)],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise ValueError("Could not rasterize SVG; convert it to PNG before publishing.") from exc
            return png_path.read_bytes(), "image/png"

    mime_type = IMAGE_TYPES.get(path.suffix.lower())
    if not mime_type:
        raise ValueError("LinkedIn image posts require JPG, PNG, or GIF media (SVG is converted to PNG).")
    return path.read_bytes(), mime_type


def _load_env_file(env_path):
    """Read simple KEY=VALUE lines without overriding process environment."""
    path = Path(env_path)
    if not path.is_file():
        return {}

    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            values[key] = value
    return values