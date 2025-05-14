message ?= "migration"
# message ?= "migration-$(shell uuidgen)"

run:
	uvicorn app:app --reload

migrations:
	alembic revision --autogenerate -m "$(message)"

migrate:
	alembic upgrade head

