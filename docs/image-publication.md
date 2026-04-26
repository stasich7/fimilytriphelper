# Image Publication

Trip plan markdown may reference remote images that are unreliable from different networks. Publish these images to the app storage before importing a version.

## Storage

The project uses MinIO as S3-compatible storage.

Local Docker Compose publishes:

- S3 API: `http://127.0.0.1:19000`
- Console: `http://127.0.0.1:19001`
- Default bucket: `family-trip-assets`

Production Docker Compose publishes only the S3 API on `127.0.0.1:19000`. The host nginx should expose it through a separate HTTPS domain, for example `https://storage.familytrip.stasich7.ru`.

## Production nginx

Create a DNS record for `storage.familytrip.stasich7.ru` pointing to the VPS. Then add an nginx server:

```nginx
server {
    listen 80;
    server_name storage.familytrip.stasich7.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name storage.familytrip.stasich7.ru;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    client_max_body_size 50m;

    location / {
        proxy_pass http://127.0.0.1:19000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

The bucket is configured for anonymous download by the `storage-init` container. Do not expose the MinIO console publicly unless it is additionally protected.

## Environment

Production `.env` should define:

```bash
MINIO_ROOT_USER=change-me
MINIO_ROOT_PASSWORD=change-me
MINIO_BUCKET=family-trip-assets
```

Local publishing can use the Docker Compose defaults:

```bash
export AWS_ACCESS_KEY_ID=family_trip_helper
export AWS_SECRET_ACCESS_KEY=family_trip_helper_storage
```

Production publishing should use the production MinIO credentials:

```bash
export AWS_ACCESS_KEY_ID="$MINIO_ROOT_USER"
export AWS_SECRET_ACCESS_KEY="$MINIO_ROOT_PASSWORD"
```

## Publish markdown images

Install the CLI dependency:

```bash
python3 -m pip install -r tools/requirements-image-publish.txt
```

Local example:

```bash
python3 tools/publish_plan_images.py \
  --input context/georgia-trip-plan-current.md \
  --output context/georgia-trip-plan-current.published.md \
  --bucket family-trip-assets \
  --prefix trips/georgia-2026-08 \
  --public-base-url http://127.0.0.1:19000 \
  --endpoint-url http://127.0.0.1:19000
```

Production example:

```bash
python3 tools/publish_plan_images.py \
  --input context/georgia-trip-plan-current.md \
  --output context/georgia-trip-plan-current.published.md \
  --bucket family-trip-assets \
  --prefix trips/georgia-2026-08 \
  --public-base-url https://storage.familytrip.stasich7.ru \
  --endpoint-url https://storage.familytrip.stasich7.ru
```

Then import `context/georgia-trip-plan-current.published.md` through the app tools.

## Behavior

- Local images such as `/maps/day.png` are left unchanged.
- Already published images under `--public-base-url` are left unchanged.
- External images are downloaded, hashed with SHA-256, and uploaded to `PREFIX/images/xx/hash.ext`.
- Public URLs are immutable and can be cached for one year.
