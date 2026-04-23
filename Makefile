.DEFAULT: update

update:
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml stop family-trip-helper-app
	git pull origin main
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml up -d family-trip-helper-app --build


stop:
	docker-compose --env-file .env -f deploy/docker-compose.prod.yml stop family-trip-helper-app