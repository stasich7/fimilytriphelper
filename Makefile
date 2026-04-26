PYTHON ?= python3
IMAGE_SOURCE ?= context/georgia-trip-plan-current.md
IMAGE_OUTPUT ?= context/georgia-trip-plan-current.published.md
IMAGE_STORAGE_BUCKET ?= family-trip-assets
IMAGE_STORAGE_PREFIX ?= trips/georgia-2026-08
IMAGE_STORAGE_PUBLIC_BASE_URL ?= http://127.0.0.1:19000
IMAGE_STORAGE_ENDPOINT_URL ?= http://127.0.0.1:19000
PROD_IMAGE_STORAGE_PUBLIC_BASE_URL ?= https://storage.familytrip.stasich7.ru

.DEFAULT: update

update:
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml stop family-trip-helper-app
	git pull origin main
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml up -d family-trip-helper-app --build


stop:
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml stop family-trip-helper-app

publish-images-local:
	$(PYTHON) tools/publish_plan_images.py \
		--input $(IMAGE_SOURCE) \
		--output $(IMAGE_OUTPUT) \
		--bucket $(IMAGE_STORAGE_BUCKET) \
		--prefix $(IMAGE_STORAGE_PREFIX) \
		--public-base-url $(IMAGE_STORAGE_PUBLIC_BASE_URL) \
		--endpoint-url $(IMAGE_STORAGE_ENDPOINT_URL) \
		--on-download-error keep-source \
		--fail-if-unpublished

verify-published-images:
	$(PYTHON) tools/publish_plan_images.py \
		--input $(IMAGE_OUTPUT) \
		--output $(IMAGE_OUTPUT) \
		--bucket $(IMAGE_STORAGE_BUCKET) \
		--prefix $(IMAGE_STORAGE_PREFIX) \
		--public-base-url $(IMAGE_STORAGE_PUBLIC_BASE_URL) \
		--endpoint-url $(IMAGE_STORAGE_ENDPOINT_URL) \
		--dry-run \
		--fail-if-unpublished

verify-prod-published-images:
	$(PYTHON) tools/publish_plan_images.py \
		--input $(IMAGE_OUTPUT) \
		--output $(IMAGE_OUTPUT) \
		--bucket $(IMAGE_STORAGE_BUCKET) \
		--prefix $(IMAGE_STORAGE_PREFIX) \
		--public-base-url $(PROD_IMAGE_STORAGE_PUBLIC_BASE_URL) \
		--endpoint-url $(IMAGE_STORAGE_ENDPOINT_URL) \
		--dry-run \
		--forbid-localhost-urls \
		--fail-if-unpublished
