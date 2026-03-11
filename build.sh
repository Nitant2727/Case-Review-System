#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create a default admin user for Render deployment
python manage.py shell -c "
from accounts.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='admin')
    print('Admin user created successfully.')

op, _ = User.objects.get_or_create(username='operator', defaults={'email':'op@example.com', 'role':'operator'})
op.set_password('operator123')
op.save()

rev, _ = User.objects.get_or_create(username='reviewer', defaults={'email':'rev@example.com', 'role':'reviewer'})
rev.set_password('reviewer123')
rev.save()

print('\n=======================================')
print(f'REVIEWER_UUID: {rev.id}')
print(f'OPERATOR_UUID: {op.id}')
print('=======================================\n')
"
