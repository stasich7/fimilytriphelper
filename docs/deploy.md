# Production Deploy

## What this setup does

- publishes the app only on `127.0.0.1:18080`
- keeps `postgres` private inside the Docker network
- runs MinIO image storage on `127.0.0.1:19000` for host nginx
- expects the host `nginx` to proxy public traffic to the app container
- runs the backend as a single app container that serves both API and frontend static files

## Requirements

- a VPS with Docker Engine and Docker Compose
- a domain or subdomain that points to the VPS
- `nginx` already running on the host and listening on `80` and `443`

## Files

- `deploy/docker-compose.prod.yml`
- `.env`

## First deploy

1. Copy the project to the VPS, for example into `/opt/family-trip-helper`.
2. Create the production env file:

```bash
cd /opt/family-trip-helper
cp .env.example .env
```

3. Edit `.env` and set:
   - `POSTGRES_PASSWORD`
   - `MINIO_ROOT_USER`
   - `MINIO_ROOT_PASSWORD`
   - `MINIO_BUCKET`

4. Start the stack:

```bash
docker compose --env-file .env -f deploy/docker-compose.prod.yml up -d --build
```

5. Check logs if needed:

```bash
docker compose --env-file .env -f deploy/docker-compose.prod.yml logs --tail=100
```

6. Add an `nginx` server for `familytrip.stasich7.ru`.

Example:

```nginx
server {
    listen 80;
    server_name familytrip.stasich7.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name familytrip.stasich7.ru;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

If you already have a matching `server` block, only the `location /` part is required.

7. Add an `nginx` server for image storage, for example `storage.familytrip.stasich7.ru`.

See `docs/image-publication.md` for the storage nginx config and image publication workflow.

## Update

```bash
cd /opt/family-trip-helper
git pull
docker compose --env-file .env -f deploy/docker-compose.prod.yml up -d --build
```

## Stop

```bash
docker compose --env-file .env -f deploy/docker-compose.prod.yml down
```

## Backup

Use `pg_dump` from the postgres container:

```bash
docker exec family-trip-helper-postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > family-trip-helper-backup.sql
```

If you run that command manually on the VPS shell, replace the environment variables with concrete values from `.env`.

## Restore

1. Create an empty database with the same name.
2. Restore into it:

```bash
cat family-trip-helper-backup.sql | docker exec -i family-trip-helper-postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

## Notes

- do not publish the postgres port to the public internet
- do not publish the MinIO console to the public internet without additional protection
- the app is intentionally bound to `127.0.0.1:18080`, so it is reachable only from the VPS itself
- the storage S3 API is intentionally bound to `127.0.0.1:19000`, so public access should go through host nginx
- guest links should be generated with the production domain in `--base-url`
- named volumes keep data across container rebuilds
