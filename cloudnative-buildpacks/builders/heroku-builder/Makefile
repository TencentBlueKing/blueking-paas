.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILDER_IMAGE_NAME ?= mirrors.tencent.com/bkpaas/builder-heroku-noble
BUILDER_TAG ?= latest

##@ Build
.PHONY: stack-noble
stack-noble:  ## Build builder/runner stack (base on heroku-24)
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-build-noble -f docker-bake.hcl
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-run-noble -f docker-bake.hcl


.PHONY: builder-noble
builder-noble: stack-noble buildpacks  ## Build cnb builder (base on heroku-24)
	pack builder create $(BUILDER_IMAGE_NAME):$(BUILDER_TAG) --config ./heroku-24.toml --pull-policy=if-not-present


.PHONY: buildpacks
buildpacks: ## Build cnb buildpacks
	cd ../../buildpacks/bk-buildpack-python && make package
	cd ../../buildpacks/bk-buildpack-nodejs && make package
	cd ../../buildpacks/bk-buildpack-go && make package
	cd ../../buildpacks/bk-buildpack-apt && make package


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
