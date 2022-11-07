#!/usr/bin/env bash
cd /paasng
# Activate TE Edition
editionctl activate TE
if [ $? -ne 0 ]; then
    echo "Unable to activate TE edition, exit now."
    exit 1
fi
echo "Try to create_legacy_db."
python create_legacy_db.py

if [ $? -ne 0 ]; then
    echo "Unable to create legacy db, exit now."
    exit 1
fi

python manage.py migrate

mkdir -p ../public/assets
python manage.py collectstatic --noinput

## Run!
command="python manage.py runserver 0.0.0.0:"$PORT
exec bash -c "$command"
