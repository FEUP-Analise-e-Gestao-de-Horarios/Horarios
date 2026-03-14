# Makefile (project root)

.PHONY: dev backend frontend

dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && pipenv run python manage.py runserver

frontend:
	cd frontend && npm run dev
