#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python3 manage.py collectstatic --no-input

# Fake the accounts 0002 migration since store_id column already exists in the DB
# TODO: Remove this line after a successful deploy
python3 manage.py migrate accounts 0002 --fake
python3 manage.py migrate
python3 manage.py create_superuser