#!/bin/sh

alembic revision --autogenerate
alembic revision --autogenerate -m "migration"

alembic upgrade head

python main.py