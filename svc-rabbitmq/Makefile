Pipfile.lock: Pipfile
	pipenv lock

requirements.txt: Pipfile.lock
	pipenv lock -r > requirements.txt

.PHONY: update
update: requirements.txt Pipfile.lock

.PHONY: image
image: requirements.txt
	docker build . -t svc_rabbitmq

.PHONY: tag
tag:
	git tag $(shell cat VERSION)
