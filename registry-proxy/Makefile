ifdef VERSION
    VERSION=${VERSION}
else
    VERSION=$(shell git describe --always 2>/dev/null || echo dev)
endif

WORKSPACE=$(shell pwd)
GO_BUILD=CGO_ENABLED=0 go build -trimpath

export PACKAGE_PATH=${WORKSPACE}/build

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

.PHONY: help
help:  ## display available make commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# formatter and linter
GOCILINT ?= $(LOCALBIN)/golangci-lint
GOCILINT_VERSION ?= v2.4.0

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
test:  ## Run the unit tests
	go test -race -count=1 ./...

.PHONY: integration
integration:  ## Run the integration tests against a local registry:2 (requires docker)
	bash hack/integration.sh

.PHONY: bench
bench: build  ## Measure streaming memory, throughput and added latency (AC-RP01 / AC-RP02)
	go run ./hack/bench -proxy-bin ${PACKAGE_PATH}/registry-proxy -size 2GiB

.PHONY: e2e-local
e2e-local:  ## Run kaniko end-to-end tests against a local registry:2 (requires docker)
	bash hack/e2e/00-build.sh && bash hack/e2e/10-local-smoke.sh

## Build
.PHONY: build
build:  ## Build the binary
	mkdir -p ${PACKAGE_PATH}
	${GO_BUILD} -ldflags "-X main.version=$(VERSION)" -o ${PACKAGE_PATH}/registry-proxy ${WORKSPACE}/cmd/registry-proxy
