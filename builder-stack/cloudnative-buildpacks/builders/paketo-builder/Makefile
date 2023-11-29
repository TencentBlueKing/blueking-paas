.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
BUILDER_IMAGE_NAME ?= mirrors.tencent.com/bkpaas/paketo-builder
IMAGE_TAG ?= bionic


##@ Build
.PHONY: builder
builder:  ## Build cnb builder
	pack builder create $(BUILDER_IMAGE_NAME):$(IMAGE_TAG) --config ./builder.toml --pull-policy=if-not-present

##@ Test 
.PHONY: integration
integration:  ## Run Intergration Test


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
