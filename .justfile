dev:
  uv run manage.py runserver

tailwind:
  pnpx @tailwindcss/cli -i ./assets/src/input.css -o ./assets/css/output.css --watch

prod:
  gunicorn currentkoi.wsgi:application

format:
  uv run ruff check --select I --fix
  uv run ruff format currentkoi apps/

makemigrations:
  python manage.py makemigrations

migrate:
  uv run manage.py migrate

makeandmigrate: makemigrations migrate

check:
  uv run manage.py check

shell:
  uv run manage.py shell -v 2
