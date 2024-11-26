#!/bin/sh

# Вернуться к базовому состоянию
echo "Returning database to initial state..."
alembic downgrade base || { echo "Alembic downgrade failed"; exit 1; }

# Сгенерировать новую миграцию
echo "Generating new migration..."
alembic revision --autogenerate -m "Initial migration" || { echo "Alembic revision failed"; exit 1; }

# Применить миграцию
echo "Upgrading database to latest version..."
alembic upgrade head || { echo "Alembic upgrade failed"; exit 1; }

# Запустить приложение
echo "Starting the application..."
python main.py || { echo "Application failed to start"; exit 1; }
