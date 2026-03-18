.PHONY: dev mirror dev-mirror prod clean-db clean-db-volume clean-mirror

mirror:
	docker compose -f docker-compose.dev.yml --profile mirror up --build mirror

dev:
	docker compose -f docker-compose.dev.yml up --build

dev-mirror:
	docker compose -f docker-compose.dev.yml --profile mirror up --build

prod:
	docker compose -f docker-compose.prod.yml up --build

clean-db:
	rm -f databases/db.sqlite3
	rm -rf databases/projects/*

clean-db-volume:
	docker volume rm pi_db_data

clean-mirror:
	docker volume rm pi_mirror_data
