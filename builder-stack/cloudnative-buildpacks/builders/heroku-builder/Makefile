.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILDER_IMAGE_NAME ?= mirrors.tencent.com/bkpaas/heroku-builder
BUILDER_TAG ?= bionic

STACK_IMAGE_NAME ?= mirrors.tencent.com/bkpaas/heroku-stack-bionic
STACK_BUILDER_TAG ?= build
STACK_RUNNER_TAG ?= run


##@ Build
.PHONY: stack-image
stack-image:  ## Build builder/runner image
	cd $(ROOT_DIR)/stack/ && IMAGE_NAME=$(STACK_IMAGE_NAME) BUILDER_TAG=$(STACK_BUILDER_TAG) docker buildx bake heroku-build -f docker-bake.hcl
	cd $(ROOT_DIR)/stack/ && IMAGE_NAME=$(STACK_IMAGE_NAME) RUNNER_TAG=$(STACK_RUNNER_TAG) docker buildx bake heroku-run -f docker-bake.hcl


.PHONY: builder
builder: stack-image ## Build cnb builder
	cd ../../buildpacks/bk-buildpack-python && make package
	cd ../../buildpacks/bk-buildpack-nodejs && make package
	cd ../../buildpacks/bk-buildpack-go && make package
	pack builder create $(BUILDER_IMAGE_NAME):$(BUILDER_TAG) --config ./builder.toml --pull-policy=if-not-present


##@ Test 
.PHONY: integration
integration:  ## Run Intergration Test


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
