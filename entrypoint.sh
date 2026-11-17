#!/bin/sh
set -e

# Automatically compile Tailwind CSS if input.css and tailwindcss binary exist
if [ -f "/app/static/css/input.css" ] && [ -x "/usr/local/bin/tailwindcss" ]; then
    echo "==> [Auto-CSS] Compiling Tailwind CSS styles.css..."
    /usr/local/bin/tailwindcss -c /app/tailwind.config.js -i /app/static/css/input.css -o /app/static/css/styles.css --minify
    echo "==> [Auto-CSS] Collecting static assets..."
    python manage.py collectstatic --noinput
    echo "==> [Auto-CSS] CSS compilation & static collection complete!"
fi

exec "$@"
