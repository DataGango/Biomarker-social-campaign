"""Preview and publish a LinkedIn member post after local confirmation."""

import argparse
from pathlib import Path

from linkedin_publisher import LinkedInConfig, LinkedInPublisher


def main():
    parser = argparse.ArgumentParser(description="Publish an approved post through LinkedIn's official API")
    parser.add_argument("--text-file", required=True, help="UTF-8 file containing the exact post text")
    parser.add_argument("--image", help="Optional JPG, PNG, GIF, or SVG image file")
    parser.add_argument("--alt-text", default="", help="Accessible description for an image post")
    args = parser.parse_args()

    text_path = Path(args.text_file).expanduser()
    if not text_path.is_file():
        parser.error("--text-file must point to an existing local file")
    commentary = text_path.read_text(encoding="utf-8").strip()
    if not commentary:
        parser.error("Post text file must not be empty")
    if args.image and not Path(args.image).expanduser().is_file():
        parser.error("--image must point to an existing local file")

    try:
        config = LinkedInConfig.from_env()
    except ValueError as exc:
        parser.error(str(exc))
    publisher = LinkedInPublisher(config)
    try:
        author_urn = publisher.resolve_author_urn()
    except Exception as exc:
        parser.error(f"Could not resolve LinkedIn member identity: {exc}")

    print("\nLinkedIn post preview")
    print(f"Author: {author_urn}")
    print("Audience: Anyone (public)")
    print("Timing: Publish now")
    print(f"Image: {Path(args.image).expanduser().resolve() if args.image else 'None (text-only)'}")
    if args.image:
        print(f"Alt text: {args.alt_text or '(not provided)'}")
    print("\n--- Post text ---")
    print(commentary)
    print("--- End preview ---\n")

    if input("Type PUBLISH to publish this exact post now: ") != "PUBLISH":
        print("Cancelled. Nothing was sent to LinkedIn.")
        return 1

    result = publisher.publish(
        commentary,
        image_path=args.image,
        alt_text=args.alt_text,
        approved=True,
    )
    print(f"Published: {result['url']}")
    print(f"Post ID: {result['post_urn']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())