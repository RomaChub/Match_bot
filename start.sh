#!/bin/sh

alembic downgrade base  # Возвращает базу данных к начальному состоянию (перед миграциями)

alembic revision --autogenerate

alembic upgrade head

python main.py