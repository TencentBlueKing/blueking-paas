.DEFAULT_GOAL := help

.PHONY: fmt
fmt: golines gofumpt ## 执行 golines，gofumpt ...
	$(GOLINES) ./ -m 119 -w --base-formatter gofmt --no-reformat-tags
	$(GOFUMPT) -l -w .

.PHONY: lint
lint: golangci-lint ## Run golangci-lint
	$(GOCILINT) run

LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

GINKGO ?= $(LOCALBIN)/ginkgo
GOLINES ?= $(LOCALBIN)/golines
GOFUMPT ?= $(LOCALBIN)/gofumpt
GOCILINT ?= $(LOCALBIN)/golangci-lint

GOCILINT_VERSION ?= v1.64.8

.PHONY: build-pind-image
build-pind-image: ## Build smart-app-builder to run in PIND mode
	docker build -t smart-app-builder:pind . -f docker-build/pind.Dockerfile

.PHONY: build-dind-image
build-dind-image:  ## Build smart-app-builder to run in DIND mode
	docker build -t smart-app-builder:dind . -f docker-build/dind.Dockerfile

.PHONY: ginkgo
ginkgo: $(GINKGO) ## install ginkgo
$(GINKGO): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/onsi/ginkgo/v2/ginkgo@v2.23.4

.PHONY: golines
golines: $(GOLINES) ## install golines
$(GOLINES): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/segmentio/golines@v0.11.0

.PHONY: gofumpt
gofumpt: $(GOFUMPT) ## install gofumpt
$(GOFUMPT): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install mvdan.cc/gofumpt@v0.4.0

.PHONY: golangci-lint
golangci-lint: $(GOCILINT) ## install golangci-lint
$(GOCILINT): $(LOCALBIN)
	test -s $(LOCALBIN)/golangci-lint && $(LOCALBIN)/golangci-lint --version | grep -q $(GOCILINT_VERSION) || \
	GOBIN=$(LOCALBIN) go install github.com/golangci/golangci-lint/cmd/golangci-lint@$(GOCILINT_VERSION)

.PHONY: test
test: ## Run unittest
	$(GINKGO) --cover --coverprofile cover.out ./...

.PHONY: help
help:  ## Show this message
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
