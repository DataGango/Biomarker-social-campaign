"""Publish an approved hosted MP4 using Instagram Login's official Reels API."""

from __future__ import annotations

import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Callable

from scripts.publish_instagram import (
    Config, PublicationError, Transport, _api_json, _http_transport,
    _resolve_account_id, resolve_campaign_file, validate_image_url,
    MAX_STATUS_CHECKS, STATUS_POLL_INTERVAL_SECONDS,
)


def validate_video_url(video_url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(video_url)
        if Path(parsed.path).suffix.lower() != ".mp4":
            raise PublicationError("IG_VIDEO_URL must end in .mp4.")
        validate_image_url(urllib.parse.urlunsplit(parsed._replace(path=parsed.path + ".jpg")))
    except (ValueError, PublicationError) as exc:
        raise PublicationError("IG_VIDEO_URL must be a public HTTPS MP4 URL without credentials, query parameters or fragments.") from exc
    return video_url


def publish_reel(
    config: Config | None,
    approval: str,
    target_alias: str,
    video_url: str,
    caption_path: Path,
    *,
    transport: Transport = _http_transport,
    output: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    if approval not in {"NO", "PUBLISH"}:
        raise PublicationError("Approval must be exactly NO or PUBLISH.")
    caption = resolve_campaign_file(caption_path, {".txt"}, "Caption file").read_text(encoding="utf-8").strip()
    if not caption or len(caption) > 2200:
        raise PublicationError("Caption must contain 1-2200 characters.")
    alias = target_alias.strip().removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9_.]+", alias):
        raise PublicationError("Provide the exact Instagram username.")
    validate_video_url(video_url)
    token = config.access_token if config else os.environ.get("IG_ACCESS_TOKEN", "").strip()

    def emit(message: str) -> None:
        output(message.replace(token, "[REDACTED]") if token else message)

    emit(f"Target account alias: {alias}")
    emit(f"Public video URL: {video_url}")
    emit("Audience: existing account settings; immediate Reel publication.")
    emit("Caption:\n" + caption)
    if approval == "NO":
        emit("Preview only. No network requests were made.")
        return None
    if config is None:
        config = Config(token, os.environ.get("IG_GRAPH_API_VERSION", "v26.0"), video_url)
    if not token or not re.fullmatch(r"v\d+\.\d+", config.graph_api_version):
        raise PublicationError("A secret IG_ACCESS_TOKEN and valid IG_GRAPH_API_VERSION are required.")

    def request(method: str, url: str, data: dict[str, str] | None = None) -> dict[str, object]:
        try:
            return _api_json(transport, method, url, token, data)
        except Exception:
            raise PublicationError("Meta API request failed; sensitive response and transport details omitted. Do not blindly retry publication.") from None

    try:
        account_id = _resolve_account_id(config, alias, transport=transport)
    except PublicationError:
        raise
    except Exception:
        raise PublicationError("Account verification failed; transport details omitted.") from None
    api_root = f"https://graph.instagram.com/{config.graph_api_version}"
    container = request("POST", f"{api_root}/{account_id}/media", {
        "media_type": "REELS", "video_url": video_url, "caption": caption,
    })
    container_id = container.get("id")
    if not isinstance(container_id, str) or not container_id.isdigit():
        raise PublicationError("Meta did not return a valid media container ID.")
    emit(f"Instagram container ID: {container_id}")
    for check_number in range(MAX_STATUS_CHECKS):
        status = request("GET", f"{api_root}/{container_id}?fields=status_code").get("status_code")
        if status == "FINISHED":
            break
        if status != "IN_PROGRESS":
            raise PublicationError("Container is not FINISHED; no publication was attempted.")
        if check_number == MAX_STATUS_CHECKS - 1:
            raise PublicationError("Container processing exceeded the bounded wait; no publication was attempted.")
        sleep(STATUS_POLL_INTERVAL_SECONDS)
    published = request("POST", f"{api_root}/{account_id}/media_publish", {"creation_id": container_id})
    media_id = published.get("id")
    if not isinstance(media_id, str) or not media_id.isdigit():
        raise PublicationError("Publish response lacked a valid media ID; reconcile the container before any retry.")
    emit(f"Published successfully. Instagram media ID: {media_id}")
    try:
        media = request("GET", f"{api_root}/{media_id}?fields=id,permalink,media_product_type")
        permalink = media.get("permalink")
        if isinstance(permalink, str) and re.fullmatch(r"https://(?:www\.)?instagram\.com/(?:reel|p)/[A-Za-z0-9_-]+/", permalink):
            emit(f"Instagram permalink: {permalink}")
        else:
            emit("Published ID confirmed; permalink unavailable. Do not republish.")
    except PublicationError:
        emit("Published ID confirmed; permalink lookup failed. Do not republish.")
    return media_id


def main() -> int:
    try:
        publish_reel(None, os.environ.get("IG_PUBLISH_APPROVAL", "NO"),
                     os.environ.get("IG_TARGET_ACCOUNT_ALIAS", ""),
                     os.environ.get("IG_VIDEO_URL", ""),
                     Path(os.environ.get("IG_CAPTION_FILE_PATH", "assets/durga-pujo-v2-caption.txt")))
    except PublicationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())