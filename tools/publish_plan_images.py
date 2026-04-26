#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import mimetypes
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import boto3
from botocore.exceptions import ClientError


IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DEFAULT_USER_AGENT = "FamilyTripHelper image publisher/1.0"
LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@dataclass(frozen=True)
class PublishedImage:
    source_url: str
    public_url: str
    object_key: str
    uploaded: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish markdown images to S3-compatible storage.")
    parser.add_argument("--input", required=True, help="Source markdown file.")
    parser.add_argument("--output", required=True, help="Markdown file with rewritten image URLs.")
    parser.add_argument("--bucket", default=os.getenv("IMAGE_STORAGE_BUCKET", "family-trip-assets"))
    parser.add_argument("--prefix", default=os.getenv("IMAGE_STORAGE_PREFIX", "trips/georgia-2026-08"))
    parser.add_argument("--public-base-url", required=True, help="Public storage base URL.")
    parser.add_argument("--endpoint-url", default=os.getenv("AWS_ENDPOINT_URL", "http://127.0.0.1:19000"))
    parser.add_argument("--access-key-id", default=os.getenv("AWS_ACCESS_KEY_ID"))
    parser.add_argument("--secret-access-key", default=os.getenv("AWS_SECRET_ACCESS_KEY"))
    parser.add_argument("--region", default=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    parser.add_argument("--cache-dir", default=".cache/published-images")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--on-download-error", choices=("fail", "keep-source"), default="fail")
    parser.add_argument(
        "--fail-if-unpublished",
        action="store_true",
        help="Exit with an error if external image URLs remain after rewriting.",
    )
    parser.add_argument(
        "--forbid-localhost-urls",
        action="store_true",
        help="Exit with an error if markdown image URLs point to localhost or loopback hosts.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def is_external_image_url(url: str, public_base_url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    return not url.startswith(public_base_url.rstrip("/") + "/")


def find_image_urls(markdown: str, public_base_url: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for match in IMAGE_PATTERN.finditer(markdown):
        url = match.group(2)
        if url in seen or not is_external_image_url(url, public_base_url):
            continue
        seen.add(url)
        urls.append(url)

    return urls


def find_localhost_image_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    for match in IMAGE_PATTERN.finditer(markdown):
        url = match.group(2)
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname in LOCALHOST_HOSTS and url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def extension_from_response(url: str, content_type: Optional[str]) -> str:
    parsed_path = urlparse(url).path
    extension = Path(parsed_path).suffix.lower()
    if extension in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}:
        return ".jpg" if extension == ".jpeg" else extension

    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return ".jpg" if guessed == ".jpeg" else guessed

    return ".img"


def download_image(url: str, cache_dir: Path, user_agent: str) -> tuple[Path, str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    response_meta_path = cache_dir / f"{cache_key}.meta"

    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type")
            data = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"download {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"download {url}: {exc.reason}") from exc

    digest = hashlib.sha256(data).hexdigest()
    extension = extension_from_response(url, content_type)
    image_path = cache_dir / f"{digest}{extension}"
    image_path.write_bytes(data)
    response_meta_path.write_text(f"{content_type or ''}\n{image_path.name}\n", encoding="utf-8")

    return image_path, digest, content_type or "application/octet-stream"


def object_exists(client, bucket: str, object_key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=object_key)
        return True
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code == 404:
            return False
        raise


def publish_images(args: argparse.Namespace, urls: Iterable[str]) -> dict[str, PublishedImage]:
    if not args.access_key_id or not args.secret_access_key:
        raise RuntimeError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")

    client = boto3.client(
        "s3",
        endpoint_url=args.endpoint_url,
        aws_access_key_id=args.access_key_id,
        aws_secret_access_key=args.secret_access_key,
        region_name=args.region,
    )

    cache_dir = Path(args.cache_dir)
    prefix = args.prefix.strip("/")
    public_base_url = args.public_base_url.rstrip("/")
    published: dict[str, PublishedImage] = {}

    for url in urls:
        try:
            image_path, digest, content_type = download_image(url, cache_dir, args.user_agent)
        except RuntimeError as exc:
            if args.on_download_error == "fail":
                raise
            print(f"warning: {exc}; keeping source URL", file=sys.stderr)
            continue

        object_key = f"{prefix}/images/{digest[:2]}/{digest}{image_path.suffix}"
        public_url = f"{public_base_url}/{args.bucket}/{object_key}"
        uploaded = False

        if not args.dry_run and not object_exists(client, args.bucket, object_key):
            client.upload_file(
                str(image_path),
                args.bucket,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
            uploaded = True

        published[url] = PublishedImage(
            source_url=url,
            public_url=public_url,
            object_key=object_key,
            uploaded=uploaded,
        )

    return published


def rewrite_markdown(markdown: str, published: dict[str, PublishedImage]) -> str:
    rewritten = markdown
    for source_url, image in published.items():
        rewritten = rewritten.replace(source_url, image.public_url)
    return rewritten


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    markdown = input_path.read_text(encoding="utf-8")
    input_localhost_urls = find_localhost_image_urls(markdown)
    if args.forbid_localhost_urls and input_localhost_urls:
        print("error: localhost image URLs are not allowed:", file=sys.stderr)
        for url in input_localhost_urls:
            print(f"- {url}", file=sys.stderr)
        return 3

    urls = find_image_urls(markdown, args.public_base_url)

    if not urls:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print("No external images found.")
        return 0

    published = publish_images(args, urls)
    rewritten = rewrite_markdown(markdown, published)
    unpublished_urls = find_image_urls(rewritten, args.public_base_url)
    localhost_urls = find_localhost_image_urls(rewritten)
    if not args.dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rewritten, encoding="utf-8")

    for image in published.values():
        status = "uploaded" if image.uploaded else "exists"
        if args.dry_run:
            status = "dry-run"
        print(f"{status}: {image.source_url} -> {image.public_url}")

    if args.fail_if_unpublished and unpublished_urls:
        print("error: external image URLs remain after publication:", file=sys.stderr)
        for url in unpublished_urls:
            print(f"- {url}", file=sys.stderr)
        return 2

    if args.forbid_localhost_urls and localhost_urls:
        print("error: localhost image URLs are not allowed:", file=sys.stderr)
        for url in localhost_urls:
            print(f"- {url}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
