.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILDER_IMAGE_NAME ?= mirrors.tencent.com/bkpaas/builder-heroku-bionic
BUILDER_TAG ?= latest

##@ Build
.PHONY: stack-bionic
stack-bionic:  ## Build builder/runner stack (base on heroku-18)
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-build-bionic -f docker-bake.hcl
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-run-bionic -f docker-bake.hcl


.PHONY: stack-jammy
stack-jammy:  ## Build builder/runner stack (base on heroku-22) **experimental**
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-build-jammy -f docker-bake.hcl
	cd $(ROOT_DIR)/stack/ && docker buildx bake heroku-run-jammy -f docker-bake.hcl


.PHONY: builder-bionic
builder-bionic: stack-bionic buildpacks ## Build cnb builder (base on heroku-18)
	pack builder create $(BUILDER_IMAGE_NAME):$(BUILDER_TAG) --config ./heroku-18.toml --pull-policy=if-not-present


.PHONY: builder-jammy
builder-jammy: stack-jammy buildpacks ## Build cnb builder (base on heroku-22) **experimental**
	pack builder create mirrors.tencent.com/bkpaas/builder-heroku-jammy:$(BUILDER_TAG) --config ./heroku-22.toml --pull-policy=if-not-present


.PHONY: buildpacks
buildpacks: ## Build cnb buildpacks
	cd ../../buildpacks/bk-buildpack-python && make package
	cd ../../buildpacks/bk-buildpack-nodejs && make package
	cd ../../buildpacks/bk-buildpack-go && make package
	cd ../../buildpacks/bk-buildpack-apt && make package


##@ Test 
.PHONY: integration
integration:  ## Run Intergration Test


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
