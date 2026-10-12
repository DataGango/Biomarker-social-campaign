"""Publish the checked-in climate poster through Meta's Instagram Graph API."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "assets"
DEFAULT_CAPTION_PATH = ASSETS_ROOT / "climate-change-instagram-caption.txt"
DEFAULT_ASSET_PATH = ASSETS_ROOT / "climate-change-instagram-poster.jpg"
ASSET_PATH = "assets/climate-change-instagram-poster.jpg"
REQUEST_TIMEOUT_SECONDS = 20
MAX_STATUS_CHECKS = 5
STATUS_POLL_INTERVAL_SECONDS = 60


class PublicationError(Exception):
    """A safe-to-display publishing or configuration error."""


@dataclass(frozen=True)
class Config:
    access_token: str
    graph_api_version: str
    image_url: str
    account_id: str | None = None


Transport = Callable[
    [str, str, dict[str, str], dict[str, str] | None, int],
    tuple[int, bytes],
]


def resolve_campaign_file(path: str | Path, allowed_suffixes: set[str], label: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ASSETS_ROOT.resolve())
    except ValueError as exc:
        raise PublicationError(f"{label} must be stored inside the repository's assets directory.") from exc
    if candidate.suffix.lower() not in allowed_suffixes or not candidate.is_file():
        suffixes = ", ".join(sorted(allowed_suffixes))
        raise PublicationError(f"{label} must be an existing file with one of these extensions: {suffixes}.")
    return candidate


def read_caption(path: Path = DEFAULT_CAPTION_PATH) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^Caption\s*\n(.*?)\n\s*Alt text\s*\n", text)
    if not match or not match.group(1).strip():
        raise PublicationError("Could not find post copy between Caption and Alt text.")
    return match.group(1).strip()


def read_alt_text(path: Path = DEFAULT_CAPTION_PATH) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^Alt text\s*\n(.*)$", text)
    return match.group(1).strip() if match else ""


def validate_image_url(image_url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(image_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise PublicationError("IG_IMAGE_URL must be a valid public HTTPS image URL.") from exc

    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise PublicationError("IG_IMAGE_URL must be a public HTTPS image URL without credentials, query parameters, or fragments.")
    if Path(parsed.path).suffix.lower() not in {".jpg", ".jpeg"}:
        raise PublicationError("Meta's current Instagram publishing API requires a JPEG image URL (.jpg or .jpeg).")
    if port not in {None, 443}:
        raise PublicationError("IG_IMAGE_URL must use the standard HTTPS port.")

    normalized_host = hostname.rstrip(".").lower()
    if normalized_host == "localhost" or normalized_host.endswith((".localhost", ".local")):
        raise PublicationError("IG_IMAGE_URL must use a publicly reachable host.")
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise PublicationError("IG_IMAGE_URL must use a publicly reachable host.")

    return image_url


def config_from_environment() -> Config:
    config = Config(
        access_token=os.environ.get("IG_ACCESS_TOKEN", "").strip(),
        graph_api_version=os.environ.get("IG_GRAPH_API_VERSION", "").strip(),
        image_url=os.environ.get("IG_IMAGE_URL", "").strip(),
        account_id=os.environ.get("IG_ACCOUNT_ID", "").strip() or None,
    )
    if not config.access_token:
        raise PublicationError("IG_ACCESS_TOKEN must be configured as a GitHub Actions secret.")
    if config.account_id is not None and not config.account_id.isdigit():
        raise PublicationError("IG_ACCOUNT_ID must be the numeric Instagram professional account ID when provided.")
    if not re.fullmatch(r"v\d+\.\d+", config.graph_api_version):
        raise PublicationError("IG_GRAPH_API_VERSION must be configured in GitHub Actions variables (for example, v25.0).")
    validate_image_url(config.image_url)
    return config


def _http_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    data: dict[str, str] | None,
    timeout: int,
) -> tuple[int, bytes]:
    encoded_data = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as exc:
        raise PublicationError("Meta API request failed; transport details were omitted.") from exc


def _api_json(
    transport: Transport,
    method: str,
    url: str,
    token: str,
    data: dict[str, str] | None = None,
) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    status, response_body = transport(method, url, headers, data, REQUEST_TIMEOUT_SECONDS)
    if not 200 <= status < 300:
        raise PublicationError(f"Meta API returned HTTP {status}; response details were omitted.")
    try:
        payload = json.loads(response_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PublicationError("Meta API returned an unreadable response.") from exc
    if not isinstance(payload, dict):
        raise PublicationError("Meta API returned an unexpected response.")
    return payload


def _resolve_account_id(
    config: Config,
    target_alias: str,
    *,
    transport: Transport,
) -> str:
    api_root = f"https://graph.instagram.com/{config.graph_api_version}"
    profile = _api_json(
        transport,
        "GET",
        f"{api_root}/me?fields=user_id,username",
        config.access_token,
    )
    if isinstance(profile.get("data"), list) and profile["data"]:
        profile = profile["data"][0]
    if not isinstance(profile, dict):
        raise PublicationError("Meta API returned an unexpected Instagram profile response.")

    resolved_id = profile.get("user_id")
    if resolved_id is None:
        resolved_id = profile.get("id")
    username = profile.get("username")
    if not isinstance(resolved_id, (str, int)) or not str(resolved_id).isdigit():
        raise PublicationError("Meta API did not return the Instagram professional account ID.")
    expected_username = target_alias.strip().removeprefix("@").casefold()
    if not isinstance(username, str) or username.strip().removeprefix("@").casefold() != expected_username:
        raise PublicationError("The authorized Instagram account does not match the approved target alias.")
    if config.account_id is not None and config.account_id != str(resolved_id):
        raise PublicationError("Configured account ID does not match the authorized Instagram account.")
    return str(resolved_id)


def publish_post(
    config: Config | None,
    approval: str | None,
    target_alias: str,
    *,
    transport: Transport = _http_transport,
    output: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    caption_path: Path = DEFAULT_CAPTION_PATH,
    asset_path: Path = DEFAULT_ASSET_PATH,
) -> str | None:
    caption = read_caption(caption_path)
    alt_text = read_alt_text(caption_path)
    validated_asset_path = resolve_campaign_file(asset_path, {".jpg", ".jpeg"}, "Poster asset")
    preview_image_url = config.image_url if config is not None else os.environ.get("IG_IMAGE_URL", "").strip()
    if preview_image_url:
        validate_image_url(preview_image_url)
    alias = target_alias.strip()
    if not alias:
        raise PublicationError("Provide the target Instagram account alias for the preview.")

    output("Instagram post preview")
    output(f"Target account alias: {alias}")
    output(f"Poster asset: {validated_asset_path.relative_to(ROOT).as_posix()}")
    if preview_image_url:
        output(f"Public image URL: {preview_image_url}")
    else:
        output("Public image URL: NOT CONFIGURED (preview only; publishing is blocked)")
    output("Caption:")
    output(caption)
    output("Alt text handoff (not sent through the publishing API):")
    output(alt_text or "No alt text provided.")

    approval_value = "NO" if approval is None else approval
    if approval_value not in {"NO", "PUBLISH"}:
        raise PublicationError("Approval must be exactly NO or PUBLISH.")
    if approval_value != "PUBLISH":
        output("Preview only. No network requests were made; choose PUBLISH to authorize an immediate post.")
        return None
    if config is None:
        config = config_from_environment()

    validated_url = validate_image_url(config.image_url)
    if not config.access_token:
        raise PublicationError("IG_ACCESS_TOKEN is required to publish.")
    if not re.fullmatch(r"v\d+\.\d+", config.graph_api_version):
        raise PublicationError("IG_GRAPH_API_VERSION must use the form vNN.N.")

    api_root = f"https://graph.instagram.com/{config.graph_api_version}"
    account_id = _resolve_account_id(config, alias, transport=transport)
    account_path = f"{api_root}/{account_id}"
    container = _api_json(
        transport,
        "POST",
        f"{account_path}/media",
        config.access_token,
        {"image_url": validated_url, "caption": caption},
    )
    container_id = container.get("id")
    if not isinstance(container_id, str) or not container_id:
        raise PublicationError("Meta API did not return a media container ID.")

    status_url = f"{api_root}/{container_id}?fields=status_code"
    for check_number in range(MAX_STATUS_CHECKS):
        status_payload = _api_json(transport, "GET", status_url, config.access_token)
        container_status = status_payload.get("status_code")
        if container_status == "FINISHED":
            break
        if container_status in {"ERROR", "EXPIRED"}:
            raise PublicationError(f"Meta media container cannot be published (status: {container_status}).")
        if container_status != "IN_PROGRESS":
            raise PublicationError("Meta API returned an unexpected media container status.")
        if check_number == MAX_STATUS_CHECKS - 1:
            raise PublicationError("Media container did not become ready within the bounded wait period.")
        sleep(STATUS_POLL_INTERVAL_SECONDS)

    published = _api_json(
        transport,
        "POST",
        f"{account_path}/media_publish",
        config.access_token,
        {"creation_id": container_id},
    )
    media_id = published.get("id")
    if not isinstance(media_id, str) or not media_id:
        raise PublicationError("Meta API did not return a published media ID.")
    output(f"Published successfully. Instagram media ID: {media_id}")
    return media_id


def main() -> int:
    approval = os.environ.get("IG_PUBLISH_APPROVAL", "NO")
    target_alias = os.environ.get("IG_TARGET_ACCOUNT_ALIAS", "")
    poster_path = os.environ.get("IG_POSTER_ASSET_PATH", ASSET_PATH)
    caption_path = os.environ.get("IG_CAPTION_FILE_PATH", "assets/climate-change-instagram-caption.txt")
    try:
        validated_poster = resolve_campaign_file(poster_path, {".jpg", ".jpeg"}, "Poster asset")
        validated_caption = resolve_campaign_file(caption_path, {".txt"}, "Caption file")
        publish_post(None, approval, target_alias, caption_path=validated_caption, asset_path=validated_poster)
    except PublicationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())