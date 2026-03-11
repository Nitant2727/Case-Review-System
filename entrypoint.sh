#!/bin/sh
set -e

echo "Waiting for database..."
python manage.py migrate --noinput

echo "Creating default admin user if not exists..."
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='admin')
    print('Admin user created.')
else:
    print('Admin user already exists.')
"

echo "Starting server..."
exec "$@"
