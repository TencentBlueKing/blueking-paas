.DEFAULT_GOAL:=help
IMAGE_NAME ?= mirrors.tencent.com/bkpaas/kaniko-executor
IMAGE_TAG ?= latest

ifeq ($(shell go env GOOS),windows)
BINARY_SUFFIX := .exe
else
BINARY_SUFFIX :=
endif

##@ Build Binary
.PHONY: build
build: launcher  ## Build all binary


.PHONY: launcher
launcher: $(LOCALBIN)  ## Build `launcher` binary
	GOOS=linux CGO_ENABLED=0 go build -o $(LOCALBIN)/launcher$(BINARY_SUFFIX) -ldflags '-extldflags "-static" -w -s' ./cmd/launcher


##@ Build Image
.PHONY: image
image:  ## Build `kaniko-executor` image
	IMAGE_NAME=$(IMAGE_NAME) IMAGE_TAG=$(IMAGE_TAG) docker buildx bake kaniko-executor -f docker-build/docker-bake.hcl


.PHONY: debug-image
debug-image:  ## Build `kaniko-executor` image
	IMAGE_NAME=$(IMAGE_NAME) IMAGE_TAG=$(IMAGE_TAG) docker buildx bake kaniko-debug-executor -f docker-build/docker-bake.hcl


##@ Test
.PHONY: test
test: ## Run unittest
	go test ./...

.PHONY: integration
integration:  ## Run Integration Test


##@ Misc
.PHONY: lint
lint: install-golangci-lint ## Run golangci-lint
	$(GOCILINT) run

## Location to build binary or install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	@mkdir -p $(LOCALBIN)

GOCILINT ?= $(LOCALBIN)/golangci-lint
.PHONY: install-golangci-lint
install-golangci-lint: $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.53.3

.PHONY: help
help:  ## Show this message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
