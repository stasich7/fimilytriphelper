#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


@dataclass(frozen=True)
class ReferencedObject:
    source_url: str
    object_key: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy markdown image objects from local S3-compatible storage to production storage."
    )
    parser.add_argument("--input", required=True, help="Markdown file that references published image objects.")
    parser.add_argument(
        "--output",
        help="Optional markdown output with source public URLs rewritten to destination public URLs.",
    )
    parser.add_argument("--bucket", default=os.getenv("IMAGE_STORAGE_BUCKET", "family-trip-assets"))
    parser.add_argument(
        "--source-public-base-url",
        default=os.getenv("LOCAL_IMAGE_STORAGE_PUBLIC_BASE_URL", "http://127.0.0.1:19000"),
    )
    parser.add_argument(
        "--dest-public-base-url",
        default=os.getenv("PROD_IMAGE_STORAGE_PUBLIC_BASE_URL", "https://storage.familytrip.stasich7.ru"),
    )
    parser.add_argument(
        "--source-endpoint-url",
        default=os.getenv("LOCAL_AWS_ENDPOINT_URL", "http://127.0.0.1:19000"),
    )
    parser.add_argument(
        "--dest-endpoint-url",
        default=os.getenv("PROD_AWS_ENDPOINT_URL", "https://storage.familytrip.stasich7.ru"),
    )
    parser.add_argument("--source-access-key-id", default=os.getenv("LOCAL_AWS_ACCESS_KEY_ID"))
    parser.add_argument("--source-secret-access-key", default=os.getenv("LOCAL_AWS_SECRET_ACCESS_KEY"))
    parser.add_argument("--dest-access-key-id", default=os.getenv("PROD_AWS_ACCESS_KEY_ID"))
    parser.add_argument("--dest-secret-access-key", default=os.getenv("PROD_AWS_SECRET_ACCESS_KEY"))
    parser.add_argument("--region", default=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    parser.add_argument("--on-missing-source", choices=("fail", "skip"), default="fail")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def s3_client(endpoint_url: str, access_key_id: str | None, secret_access_key: str | None, region: str):
    if not access_key_id or not secret_access_key:
        raise RuntimeError("source and destination access keys are required")

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
        config=Config(s3={"addressing_style": "path"}),
    )


def extract_object_key(url: str, bucket: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    path = parsed.path.lstrip("/")
    bucket_prefix = f"{bucket}/"
    if not path.startswith(bucket_prefix):
        return None

    object_key = path[len(bucket_prefix) :]
    return object_key or None


def find_referenced_objects(markdown: str, bucket: str) -> list[ReferencedObject]:
    objects: list[ReferencedObject] = []
    seen: set[str] = set()

    for match in IMAGE_PATTERN.finditer(markdown):
        url = match.group(2)
        object_key = extract_object_key(url, bucket)
        if not object_key or object_key in seen:
            continue
        seen.add(object_key)
        objects.append(ReferencedObject(source_url=url, object_key=object_key))

    return objects


def object_exists(client, bucket: str, object_key: str) -> bool:
    try:
        client.head_object(Bucket=bucket, Key=object_key)
        return True
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code == 404:
            return False
        raise


def copy_object(source_client, dest_client, bucket: str, object_key: str, dry_run: bool) -> str:
    if object_exists(dest_client, bucket, object_key):
        return "exists"

    if dry_run:
        return "dry-run"

    source_object = source_client.get_object(Bucket=bucket, Key=object_key)
    metadata = {
        "ContentType": source_object.get("ContentType", "application/octet-stream"),
        "CacheControl": source_object.get("CacheControl", "public, max-age=31536000, immutable"),
    }
    dest_client.put_object(
        Bucket=bucket,
        Key=object_key,
        Body=source_object["Body"].read(),
        **metadata,
    )
    return "copied"


def rewrite_markdown(markdown: str, source_public_base_url: str, dest_public_base_url: str) -> str:
    source_base = source_public_base_url.rstrip("/") + "/"
    dest_base = dest_public_base_url.rstrip("/") + "/"
    return markdown.replace(source_base, dest_base)


def main() -> int:
    args = parse_args()
    markdown = Path(args.input).read_text(encoding="utf-8")
    referenced_objects = find_referenced_objects(markdown, args.bucket)

    if not referenced_objects:
        print("No S3 image objects found in markdown.")
        return 0

    source_client = s3_client(
        args.source_endpoint_url,
        args.source_access_key_id,
        args.source_secret_access_key,
        args.region,
    )
    dest_client = s3_client(
        args.dest_endpoint_url,
        args.dest_access_key_id,
        args.dest_secret_access_key,
        args.region,
    )

    failed = False
    for referenced_object in referenced_objects:
        try:
            status = copy_object(source_client, dest_client, args.bucket, referenced_object.object_key, args.dry_run)
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 404 and args.on_missing_source == "skip":
                print(f"missing-source: {referenced_object.object_key}", file=sys.stderr)
                continue
            failed = True
            print(f"error: copy {referenced_object.object_key}: {exc}", file=sys.stderr)
            continue

        print(f"{status}: {referenced_object.object_key}")

    if args.output:
        rewritten = rewrite_markdown(markdown, args.source_public_base_url, args.dest_public_base_url)
        if not args.dry_run:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rewritten, encoding="utf-8")
        print(f"markdown-output: {args.output}")

    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
