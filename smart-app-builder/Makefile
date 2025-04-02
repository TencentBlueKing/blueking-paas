.DEFAULT_GOAL := help

.PHONY: build-pind-image
build-pind-image: ## Build smart-app-builder to run in PIND mode
	docker build -t smart-app-builder:pind . -f docker-build/pind.Dockerfile

.PHONY: build-dind-image
build-dind-image:  ## Build smart-app-builder to run in DIND mode
	docker build -t smart-app-builder:dind . -f docker-build/dind.Dockerfile

.PHONY: test
test: ## Run unittest
	ginkgo ./...

.PHONY: help
help:  ## Show this message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
