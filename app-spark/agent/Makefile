IMAGE_NAME ?= app-spark-agent
IMAGE_TAG ?= dev
# Registry URL is injected by the pipeline; this is a placeholder, no credentials.
IMAGE_REPO ?= registry.example.com/app-spark/app-spark-agent

.PHONY: help
help: ## Show available make targets
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

.PHONY: fmt
fmt: ## Format Python sources
	uv run ruff format .
	uv run ruff check --select I --fix .

.PHONY: lint
lint: ## Lint Python sources
	uv run ruff check .

.PHONY: typecheck
typecheck: ## Run mypy
	uv run mypy --config-file=./pyproject.toml

.PHONY: test
test: ## Run unit tests (excludes e2e)
	uv run pytest tests/

.PHONY: run
run: ## Start the Agent HTTP server
	uv run python -m app_spark_agent

##@ Build

.PHONY: docker-build
docker-build: ## Build the local Agent image
	docker build --load -t $(IMAGE_NAME):dev .

.PHONY: docker-push
docker-push: ## Tag and push the Agent image (IMAGE_REPO / IMAGE_TAG)
	docker tag $(IMAGE_NAME):dev $(IMAGE_REPO):$(IMAGE_TAG)
	docker push $(IMAGE_REPO):$(IMAGE_TAG)
