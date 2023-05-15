# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#   http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

ifdef VERSION
    VERSION=${VERSION}
else
    VERSION=$(shell git describe --always)
endif

ifdef GITCOMMIT
    GITCOMMIT=${GITCOMMIT}
else
    GITCOMMIT=$(shell git rev-parse HEAD)
endif

ifdef GOOS
    GOOS=${GOOS}
else
    GOOS=""
endif

ifdef GOARCH
    GOARCH=${GOARCH}
else
    GOARCH=""
endif

ifeq (${GOOS}, windows)
    BIN_NAME=bkpaas-cli.exe
else
    BIN_NAME=bkpaas-cli
endif


## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

BUILDTIME=${shell date +%Y-%m-%dT%H:%M:%S%z}

LDFLAGS="-X github.com/TencentBlueKing/blueking-paas/client/pkg/version.Version=${VERSION} \
	-X github.com/TencentBlueKing/blueking-paas/client/pkg/version.GitCommit=${GITCOMMIT} \
	-X github.com/TencentBlueKing/blueking-paas/client/pkg/version.BuildTime=${BUILDTIME}"

GINKGO ?= $(LOCALBIN)/ginkgo
GOLINES ?= $(LOCALBIN)/golines
GOFUMPT ?= $(LOCALBIN)/gofumpt
GOCILINT ?= $(LOCALBIN)/golangci-lint

.PHONY: help
help: ## 展示可用 make 命令及说明
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 开发/构建命令

.PHONY: build
build: tidy ## 构建 bkpaas-cli 可执行文件
	CGO_ENABLED=0 GOOS=${GOOS} GOARCH=${GOARCH} go build -ldflags ${LDFLAGS} -o ${BIN_NAME} ./main.go

.PHONY: fmt
fmt: ## 执行 golines，gofumpt ...
	$(GOLINES) ./ -m 119 -w --base-formatter gofmt --no-reformat-tags
	$(GOFUMPT) -l -w .

.PHONY: vet
vet: ## 执行 go vet ./...
	go vet ./...

.PHONY: tidy
tidy: ## 执行 go mod tidy
	go mod tidy

.PHONY: test
test: tidy ## 执行 ginkgo 单元测试
	$(GINKGO) --cover --coverprofile cover.out ./...

.PHONY: lint
lint: ## 执行 golangci-lint run
	$(GOCILINT) run

##@ 开发工具安装命令

.PHONY: install-ginkgo
install-ginkgo: $(GINKGO) ## 下载 ginkgo 二进制
$(GINKGO): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/onsi/ginkgo/v2/ginkgo@v2.1.4

.PHONY: install-golines
install-golines: $(GOLINES) ## 下载 golines 二进制
$(GOLINES): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/segmentio/golines@v0.11.0

.PHONY: install-gofumpt
install-gofumpt: $(GOFUMPT) ## 下载 gofumpt 二进制
$(GOFUMPT): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install mvdan.cc/gofumpt@v0.4.0

.PHONY: install-golangci-lint
install-golangci-lint: $(GOCILINT) ## 下载 golangci-lint 二进制
$(GOCILINT): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.47.3
