#!/usr/bin/env bash
# Exit on error
set -e

python manage.py migrate
python manage.py loaddata data/fixtures/plans.json data/fixtures/service.json