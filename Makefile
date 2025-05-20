message ?= "migration"
# message ?= "migration-$(shell uuidgen)"

run:
	uvicorn server.main:app --reload

migrations:
	alembic revision --autogenerate -m "$(message)"

migrate:
	alembic upgrade head

