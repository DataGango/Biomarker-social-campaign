"""Publish one approved photo or Reel to a verified Facebook Page."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "assets"
REQUEST_TIMEOUT_SECONDS = 90
MAX_STATUS_CHECKS = 20
STATUS_POLL_INTERVAL_SECONDS = 15
MAX_REEL_POSTS_PER_24_HOURS = 30


class PublicationError(Exception):
    """Safe-to-display Facebook Page publishing error."""


Transport = Callable[
    [str, str, dict[str, str], bytes | None, int],
    tuple[int, bytes],
]


def resolve_asset(path: str | Path, media_kind: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ASSETS_ROOT.resolve())
    except ValueError as exc:
        raise PublicationError("Media asset must be inside the repository's assets directory.") from exc

    allowed = {"photo": {".jpg", ".jpeg", ".png"}, "reel": {".mp4"}}
    if media_kind not in allowed or candidate.suffix.lower() not in allowed[media_kind]:
        raise PublicationError("Media asset extension does not match the selected Facebook post type.")
    if not candidate.is_file() or candidate.stat().st_size == 0:
        raise PublicationError("Media asset must be an existing, non-empty file.")
    return candidate


def read_caption(path: str | Path) -> str:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ASSETS_ROOT.resolve())
    except ValueError as exc:
        raise PublicationError("Caption file must be inside the repository's assets directory.") from exc
    if candidate.suffix.lower() != ".txt" or not candidate.is_file():
        raise PublicationError("Caption must be an existing .txt file inside assets/.")
    caption = candidate.read_text(encoding="utf-8").strip()
    if not caption:
        raise PublicationError("Caption file must not be empty.")
    return caption


def _http_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    timeout: int,
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except Exception as exc:
        raise PublicationError("Facebook request failed; transport details were omitted.") from exc


def _decode_json(status: int, body: bytes) -> dict[str, object]:
    if not 200 <= status < 300:
        raise PublicationError(f"Facebook Graph API returned HTTP {status}; response details were omitted.")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PublicationError("Facebook returned an unreadable response.") from exc
    if not isinstance(payload, dict):
        raise PublicationError("Facebook returned an unexpected response.")
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        code_text = f" (code {code})" if isinstance(code, (int, str)) else ""
        raise PublicationError(f"Facebook rejected the request{code_text}; response details were omitted.")
    return payload


def _form_body(data: dict[str, str]) -> bytes:
    return urllib.parse.urlencode(data).encode("utf-8")


def _api_json(
    transport: Transport,
    method: str,
    url: str,
    token: str,
    data: dict[str, str] | bytes | None = None,
    content_type: str | None = None,
) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {token}"}
    body = data
    if isinstance(data, dict):
        body = _form_body(data)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif isinstance(data, bytes):
        headers["Content-Type"] = content_type or "application/octet-stream"
    try:
        status, response_body = transport(method, url, headers, body, REQUEST_TIMEOUT_SECONDS)
        return _decode_json(status, response_body)
    except PublicationError:
        raise
    except Exception as exc:
        raise PublicationError("Facebook API request failed; transport details were omitted.") from exc


def _multipart_photo(asset: Path, caption: str) -> tuple[bytes, str]:
    boundary = "----------------fb" + uuid.uuid4().hex
    mime_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"published\"\r\n\r\ntrue\r\n".encode("ascii"),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"{asset.name}\"\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8"),
        asset.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode("ascii"),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _validate_page(page: dict[str, object], expected_id: str, expected_name: str) -> str:
    page_id = page.get("id")
    page_name = page.get("name")
    if not isinstance(page_id, (str, int)) or not str(page_id).isdigit():
        raise PublicationError("Page access token did not resolve to a valid Page ID.")
    if str(page_id) != expected_id:
        raise PublicationError("Authorized Page ID does not match the approved destination.")
    if not isinstance(page_name, str) or page_name.strip().casefold() != expected_name.strip().casefold():
        raise PublicationError("Authorized Page name does not match the approved destination.")
    return str(page_id)


def _status_ready(payload: dict[str, object]) -> bool:
    status = payload.get("status")
    if not isinstance(status, dict):
        raise PublicationError("Facebook Reel status response was missing required status details.")
    video_status = status.get("video_status")
    if video_status in {"error", "expired", "upload_failed"}:
        raise PublicationError("Facebook Reel upload or processing failed; no publish step was attempted.")
    uploading = status.get("uploading_phase")
    processing = status.get("processing_phase")
    upload_status = uploading.get("status") if isinstance(uploading, dict) else None
    processing_status = processing.get("status") if isinstance(processing, dict) else None
    if upload_status == "error" or processing_status == "error":
        raise PublicationError("Facebook Reel upload or processing failed; no publish step was attempted.")
    return video_status == "ready" or (
        upload_status in {"complete", "completed"}
        and processing_status in {"complete", "completed"}
    )


def publish_page_post(
    approval: str,
    media_kind: str,
    page_id: str,
    page_name: str,
    asset_path: str | Path,
    caption_path: str | Path,
    *,
    title: str = "Optogenetics: light and selected neural circuits",
    token: str | None = None,
    graph_version: str | None = None,
    transport: Transport = _http_transport,
    output: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    if approval not in {"NO", "PUBLISH"}:
        raise PublicationError("Approval must be exactly NO or PUBLISH.")
    if media_kind not in {"photo", "reel"}:
        raise PublicationError("Post type must be photo or reel.")
    if not re.fullmatch(r"\d+", page_id.strip()):
        raise PublicationError("Provide the numeric Facebook Page ID from the approved destination.")
    expected_name = page_name.strip()
    if not expected_name:
        raise PublicationError("Provide the exact Facebook Page name for identity verification.")
    asset = resolve_asset(asset_path, media_kind)
    caption = read_caption(caption_path)
    if media_kind == "reel" and not title.strip():
        raise PublicationError("Reels require a non-empty title.")

    output("Facebook Page post preview")
    output(f"Destination Page: {expected_name} (ID {page_id.strip()})")
    output("Audience: Public Page audience")
    output("Timing: Immediate after protected GitHub environment approval")
    output(f"Post type: {media_kind}")
    output(f"Asset: {asset.relative_to(ROOT).as_posix()} ({asset.stat().st_size} bytes)")
    if media_kind == "reel":
        output(f"Reel title: {title.strip()}")
    output("Caption:")
    output(caption)
    if approval == "NO":
        output("Preview only. No network requests were made.")
        return None

    access_token = (token if token is not None else os.environ.get("FB_PAGE_ACCESS_TOKEN", "")).strip()
    version = (graph_version if graph_version is not None else os.environ.get("FB_GRAPH_API_VERSION", "v26.0")).strip()
    if not access_token:
        raise PublicationError("FB_PAGE_ACCESS_TOKEN must be configured as a protected GitHub Actions secret.")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise PublicationError("FB_GRAPH_API_VERSION must have the form vNN.N.")

    api_root = f"https://graph.facebook.com/{version}"
    page_payload = _api_json(transport, "GET", f"{api_root}/me?fields=id,name", access_token)
    resolved_page_id = _validate_page(page_payload, page_id.strip(), expected_name)
    output(f"Verified Page identity: {expected_name} (ID {resolved_page_id})")

    if media_kind == "photo":
        body, content_type = _multipart_photo(asset, caption)
        try:
            response = _api_json(
                transport,
                "POST",
                f"{api_root}/{resolved_page_id}/photos",
                access_token,
                body,
                content_type,
            )
        except PublicationError as exc:
            raise PublicationError(f"Photo publish response is uncertain or failed: {exc} Do not retry until the Page is reconciled.") from None
        photo_id = response.get("id")
        post_id = response.get("post_id")
        if not isinstance(photo_id, (str, int)) or not str(photo_id).isdigit():
            raise PublicationError("Facebook did not confirm a photo ID; reconcile the Page before any retry.")
        output(f"Published successfully. Facebook Page photo ID: {photo_id}")
        if isinstance(post_id, str) and post_id:
            output(f"Facebook Page post ID: {post_id}")
            return post_id
        return str(photo_id)

    start = _api_json(
        transport,
        "POST",
        f"{api_root}/{resolved_page_id}/video_reels",
        access_token,
        {"upload_phase": "start"},
    )
    video_id = start.get("video_id")
    upload_url = start.get("upload_url")
    if not isinstance(video_id, (str, int)) or not str(video_id).isdigit():
        raise PublicationError("Facebook did not return a valid Reel upload ID.")
    if not isinstance(upload_url, str):
        raise PublicationError("Facebook did not return a Reel upload URL.")
    parsed_upload = urllib.parse.urlsplit(upload_url)
    if (
        parsed_upload.scheme != "https"
        or parsed_upload.hostname != "rupload.facebook.com"
        or str(video_id) not in parsed_upload.path
        or parsed_upload.query
        or parsed_upload.fragment
    ):
        raise PublicationError("Facebook returned an unsafe or unexpected Reel upload URL.")
    output(f"Facebook Reel upload session: {video_id}")

    video_bytes = asset.read_bytes()
    upload_headers = {
        "Authorization": f"OAuth {access_token}",
        "Content-Type": "application/octet-stream",
        "offset": "0",
        "file_size": str(len(video_bytes)),
    }
    try:
        upload_status, upload_body = transport(
            "POST", upload_url, upload_headers, video_bytes, REQUEST_TIMEOUT_SECONDS
        )
    except Exception:
        raise PublicationError("Facebook Reel upload failed; transport details omitted. Do not retry this session blindly.") from None
    upload_result = _decode_json(upload_status, upload_body)
    if upload_result.get("success") is not True:
        raise PublicationError("Facebook did not confirm Reel bytes upload; no publish step was attempted.")

    for check_number in range(MAX_STATUS_CHECKS):
        status_payload = _api_json(
            transport,
            "GET",
            f"{api_root}/{video_id}?fields=status",
            access_token,
        )
        if _status_ready(status_payload):
            break
        if check_number == MAX_STATUS_CHECKS - 1:
            raise PublicationError("Facebook Reel did not become ready within the bounded wait; no publish step was attempted.")
        sleep(STATUS_POLL_INTERVAL_SECONDS)

    try:
        finish = _api_json(
            transport,
            "POST",
            f"{api_root}/{resolved_page_id}/video_reels",
            access_token,
            {
                "upload_phase": "finish",
                "video_id": str(video_id),
                "video_state": "PUBLISHED",
                "title": title.strip(),
                "description": caption,
            },
        )
    except PublicationError as exc:
        raise PublicationError(f"Facebook Reel finish response is uncertain: {exc} Reconcile video ID {video_id} before retrying.") from None
    if finish.get("success") is not True:
        raise PublicationError(f"Facebook did not confirm Reel publication for video ID {video_id}; reconcile before retrying.")
    output(f"Published successfully. Facebook Page Reel video ID: {video_id}")
    output("Meta accepted the finish request. Reconcile the Page Reel list before any retry.")
    return str(video_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or publish an approved Facebook Page photo or Reel.")
    parser.add_argument("--approval", choices=("NO", "PUBLISH"), default=os.environ.get("FB_PUBLISH_APPROVAL", "NO"))
    parser.add_argument("--media-kind", choices=("photo", "reel"), required=True)
    parser.add_argument("--page-id", default=os.environ.get("FB_PAGE_ID", ""))
    parser.add_argument("--page-name", default=os.environ.get("FB_PAGE_NAME", ""))
    parser.add_argument("--asset", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--title", default="Optogenetics: light and selected neural circuits")
    args = parser.parse_args()
    try:
        publish_page_post(
            args.approval,
            args.media_kind,
            args.page_id,
            args.page_name,
            args.asset,
            args.caption,
            title=args.title,
        )
    except PublicationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())