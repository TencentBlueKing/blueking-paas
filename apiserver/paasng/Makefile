.PHONY: test
test:
	DJANGO_SETTINGS_MODULE='paasng.settings' pytest -l -p no:warnings --reuse-db --maxfail=1 tests/

.PHONY: edition
edition:
	editionctl info

.PHONY: edition-te
edition-te:
	editionctl activate TE

.PHONY: edition-ee
edition-ee:
	editionctl activate EE

.PHONY: edition-develop
edition-develop:
	editionctl develop

.PHONY: edition-reset
edition-reset:
	editionctl reset

# make messages of python file and django template file to django.po
# python manage.py makemessages -d django -l zh-cn -e html,part -e py
i18n_tpl:
	python manage.py makemessages -d django -l en -e html,part -e py

# compile django.po and djangojs.po to django.mo and djangojs.mo
i18n_mo:
	python manage.py compilemessages
