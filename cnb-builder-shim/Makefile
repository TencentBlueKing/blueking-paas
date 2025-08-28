.DEFAULT_GOAL:=help

ifeq ($(shell go env GOOS),windows)
BINARY_SUFFIX := .exe
else
BINARY_SUFFIX :=
endif

##@ Build Binary
.PHONY: build
build: build-init lifecycle-driver entrypoint  ## Build all binary


.PHONY: build-dev
build-dev: dev-entrypoint lifecycle-driver dev-launcher


.PHONY: build-init
build-init: $(LOCALBIN)  ## Build `build-init` binary
	go build -o $(LOCALBIN)/build-init$(BINARY_SUFFIX) ./cmd/build-init


.PHONY: lifecycle-driver
lifecycle-driver: $(LOCALBIN)  ## Build `lifecycle-driver` binary
	go build -o $(LOCALBIN)/lifecycle-driver$(BINARY_SUFFIX) ./cmd/lifecycle-driver


.PHONY: entrypoint
entrypoint: $(LOCALBIN) ## Build `entrypoint` binary
	go build -o $(LOCALBIN)/entrypoint ./cmd/entrypoint


.PHONY: dev-entrypoint
dev-entrypoint:
	go build -o $(LOCALBIN)/dev-entrypoint ./cmd/dev-entrypoint


.PHONY: dev-launcher
dev-launcher:
	go build -o $(LOCALBIN)/dev-launcher ./cmd/dev-launcher


##@ Build Image
.PHONY: heroku-builder-noble
heroku-builder-noble:  ## Build builder image which is based on `cloudnative-buildpacks/builders/heroku-builder`
	docker buildx bake heroku-builder-noble -f docker-build/heroku-builder/docker-bake.hcl


.PHONY: heroku-dev
heroku-dev:  ## Build dev sandbox image which is based on `cloudnative-buildpacks/builders/heroku-builder`
	docker buildx bake heroku-dev -f docker-build/heroku-builder/docker-bake.hcl


##@ Test
.PHONY: test
test: ## Run unittest
	go test ./...


.PHONY: integration
integration:  ## Run Integration Test
	echo "Not implemented yet..."

##@ Misc
.PHONY: fmt
fmt: golines gofumpt ## 执行 golines，gofumpt ...
	$(GOLINES) ./ -m 119 -w --base-formatter gofmt --no-reformat-tags
	$(GOFUMPT) -l -w .

.PHONY: lint
lint: golangci-lint ## Run golangci-lint
	$(GOCILINT) run

## Location to build binary or install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	@mkdir -p $(LOCALBIN)

GOLINES ?= $(LOCALBIN)/golines
GOFUMPT ?= $(LOCALBIN)/gofumpt
GOCILINT ?= $(LOCALBIN)/golangci-lint

GOCILINT_VERSION ?= v2.4.0

.PHONY: golines
golines: $(GOLINES) ## install golines
$(GOLINES): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/segmentio/golines@v0.11.0

.PHONY: gofumpt
gofumpt: $(GOFUMPT) ## install gofumpt
$(GOFUMPT): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install mvdan.cc/gofumpt@v0.4.0

.PHONY: golangci-lint
golangci-lint: $(LOCALBIN) ## install golangci-lint
	test -s $(LOCALBIN)/golangci-lint && $(LOCALBIN)/golangci-lint --version | grep -q $(GOCILINT_VERSION) || \
	GOBIN=$(LOCALBIN) go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@$(GOCILINT_VERSION)


.PHONY: help
help:  ## Show this message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
