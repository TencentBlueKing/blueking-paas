IMAGE_NAME ?= app-spark-agent
IMAGE_TAG ?= dev
# Registry URL is injected by the pipeline; this is a placeholder, no credentials.
IMAGE_REPO ?= registry.example.com/app-spark/app-spark-agent
# The cube base image envd is copied from; its tag must match the platform's ENVD_REF.
# Required, with no default, so that no build silently picks an envd the platform never validated.
CUBE_BASE_ENVD_IMAGE ?=
# envd in the cube base image is linux/amd64 only.
IMAGE_PLATFORM ?= linux/amd64

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

.PHONY: update-gitignore-assets
update-gitignore-assets: ## Refresh vendored github/gitignore templates in git/assets
	uv run python -m app_spark_agent.git.update_assets

##@ Build

.PHONY: docker-build
docker-build: ## Build the local Agent image (requires CUBE_BASE_ENVD_IMAGE)
	$(if $(CUBE_BASE_ENVD_IMAGE),,$(error CUBE_BASE_ENVD_IMAGE is required, e.g. make docker-build CUBE_BASE_ENVD_IMAGE=<registry>/cube-base-envd:<ENVD_REF>))
	docker build --load --platform $(IMAGE_PLATFORM) \
		--build-arg CUBE_BASE_ENVD_IMAGE=$(CUBE_BASE_ENVD_IMAGE) \
		-t $(IMAGE_NAME):dev .

.PHONY: docker-push
docker-push: ## Tag and push the Agent image (IMAGE_REPO / IMAGE_TAG)
	docker tag $(IMAGE_NAME):dev $(IMAGE_REPO):$(IMAGE_TAG)
	docker push $(IMAGE_REPO):$(IMAGE_TAG)
