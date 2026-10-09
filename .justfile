dev:
  python manage.py runserver

tailwind:
  pnpx @tailwindcss/cli -i ./assets/css/input.css -o ./assets/css/output.css --watch

prod:
  gunicorn currentkoi.wsgi:application

format:
  uv run ruff check --select I --fix
  uv run ruff format currentkoi apps/

makemigrations:
  python manage.py makemigrations

migrate:
  python manage.py migrate

makeandmigrate: makemigrations migrate

check:
  python manage.py check

shell:
  python manage.py shell -v 2
