VERSION ?= $(shell git describe --always)
GIT_HASH ?= $(shell git rev-parse HEAD)

WORKSPACE=$(shell pwd)
BUILD_TIME=$(shell date +%Y-%m-%dT%I:%M:%S)
GO_BUILD=CGO_ENABLED=0 go build -trimpath

# build path config
export PACKAGE_PATH=${WORKSPACE}/build

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

.PHONY: help
help:  ## display available make commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# Tool binaries
# All tools used by current project are installed in $(LOCALBIN)
GINKGO ?= $(LOCALBIN)/ginkgo
GINKGO_VERSION ?= v2.28.1

# formatter and linter
GOCILINT ?= $(LOCALBIN)/golangci-lint
GOCILINT_VERSION ?= v2.4.0

# swagger doc generator
SWAG ?= $(LOCALBIN)/swag
SWAG_VERSION ?= latest

## Format
.PHONY: fmt
fmt: golangci-lint  ## Format the code
	$(GOCILINT) fmt .

.PHONY: lint
lint: golangci-lint  ## Lint the code
	$(GOCILINT) run

.PHONY: golangci-lint
golangci-lint: $(GOCILINT)  ## install golangci-lint tool
$(GOCILINT): $(LOCALBIN)
	test -s $(LOCALBIN)/golangci-lint && $(LOCALBIN)/golangci-lint --version | grep -q $(GOCILINT_VERSION) || \
	curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/HEAD/install.sh | sh -s -- -b $(LOCALBIN) $(GOCILINT_VERSION)

## Test
.PHONY: test
test: ginkgo  ## Run the tests
	$(GINKGO) -gcflags="all=-l -N" --cover --coverprofile cover.out ./...

.PHONY: ginkgo
ginkgo: $(GINKGO)  ## install ginkgo tool
$(GINKGO): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/onsi/ginkgo/v2/ginkgo@$(GINKGO_VERSION)

## Docs
.PHONY: swag-init
swag-init: $(SWAG)  ## Generate swagger documentation
	$(SWAG) fmt && $(SWAG) init --parseDependency --parseInternal --parseDepth 1 -o docs -g cmd/main.go

.PHONY: swag
swag: $(SWAG)  ## install swag tool
$(SWAG): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/swaggo/swag/cmd/swag@$(SWAG_VERSION)

## Build
.PHONY: build
build: swag-init ## Build the binary
	mkdir -p ${PACKAGE_PATH}
	${GO_BUILD} -o ${PACKAGE_PATH}/daemon ${WORKSPACE}/cmd/main.go
