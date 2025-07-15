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

# docker build，push，deploy 使用到的 controller 镜像 Tag
IMG ?= controller:latest
# envtest 二进制指定的需要下载的 kubebuilder 版本
ENVTEST_K8S_VERSION = 1.24.1
# 在部署时会关联到 controller Deployment 的 imagePullSecrets
DOCKER_CONFIG_JSON ?= ""
# 待自动更新的 helm chart 目标目录
HELM_CHART_TARGET_DIR ?= "/tmp/bkpaas-app-operator"

ifdef VERSION
    VERSION=${VERSION}
else
    VERSION=$(shell git describe --always)
endif

# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
GOBIN=$(shell go env GOPATH)/bin
else
GOBIN=$(shell go env GOBIN)
endif

# Setting SHELL to bash allows bash commands to be executed by recipes.
# This is a requirement for 'setup-envtest.sh' in the test target.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

.PHONY: all
all: build

##@ General

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
# More info on the usage of ANSI control characters for terminal formatting:
# https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters
# More info on the awk command:
# http://linuxcommand.org/lc3_adv_awk.php

.PHONY: help
help: ## 展示可用 make 命令及说明
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 研发命令

.PHONY: manifests
manifests: controller-gen ## 生成 WebhookConfiguration，ClusterRole，CustomResourceDefinition 等配置（YAML）
	# 备注：output:none 将会丢弃其他的输出，适用于仅特定配置如 crd，webhook 需要更新的情况。
	# 如果需要增加更新其他部分的 manifests 文件，请在 output:none 前追加对应参数。
	# 参考： https://book.kubebuilder.io/reference/controller-gen.html#output-rules
	$(CONTROLLER_GEN) paths="./..." crd:crdVersions=v1 webhook rbac:roleName=manager-role output:crd:artifacts:config=config/crd/bases output:webhook:artifacts:config=config/webhook output:rbac:artifacts:config=config/rbac output:none

.PHONY: generate
generate: controller-gen ## 生成 DeepCopy，DeepCopyInto，DeepCopyObject 代码实现（Go）
	$(CONTROLLER_GEN) object:headerFile="hack/boilerplate.go.txt" paths="./..."

.PHONY: fmt
fmt: golines gofumpt ## 执行 golines，gofumpt ...
	$(GOLINES) ./ -m 119 -w --base-formatter gofmt --no-reformat-tags
	$(GOFUMPT) -l -w .

.PHONY: vet
vet: ## 执行 go vet ./...
	go vet ./...

.PHONY: tidy
tidy: ## 执行 go mod tidy
	go mod tidy

.PHONY: test
test: manifests generate fmt vet envtest ginkgo ## 执行 go test ./... 并输出覆盖率报告
	KUBEBUILDER_ASSETS="$(shell $(ENVTEST) use $(ENVTEST_K8S_VERSION) -p path)" \
	$(GINKGO) --cover --coverprofile cover.out ./...

.PHONY: lint
lint: golangci-lint ## 执行 golangci-lint run
	$(GOCILINT) run

.PHONY: update-helm-chart
update-helm-chart: manifests ## 根据 kustomize 渲染出的 manifest，更新 helm-charts
	rm -rf ./bkpaas-app-operator
	$(KUSTOMIZE) build config/default | $(HELMIFY) bkpaas-app-operator
	python3 ./scripts/update_helm_chart.py -d ${HELM_CHART_TARGET_DIR}

##@ 构建命令

gitVersion ?= $(shell git describe --tags --always --dirty)
gitCommit ?= $(shell git rev-parse HEAD)
gitTreeState ?= $(if $(shell git status --porcelain),"dirty","clean")
goVersion ?= $(shell go version | awk '{print $$3}')
buildTime ?= $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')

ldflags="-X main.gitVersion=$(gitVersion) \
	-X main.gitCommit=$(gitCommit) \
	-X main.gitTreeState=$(gitTreeState) \
	-X main.goVersion=$(goVersion) \
	-X main.buildTime=$(buildTime)"

.PHONY: build
build: generate fmt vet ## 构建 Manager 二进制
	go build -ldflags $(ldflags) -o bin/manager main.go

.PHONY: run
run: manifests generate fmt vet ## 本地运行 Controller（现阶段需要添加环境变量 ENABLE_WEBHOOKS=false）
	go run main.go

.PHONY: docker-build
docker-build: ## 构建 Manager 镜像，需指定 IMG 参数
	docker build -t ${IMG} --no-cache .

.PHONY: docker-push
docker-push: ## 推送 Manager 镜像，需指定 IMG 参数
	docker push ${IMG}

.PHONY: docker-dev
docker-dev: ## 构建用于执行开发调试 / 单元测试的 docker 镜像
	docker build -f ./Dockerfile-Dev -t bkpaas-app-operator-dev:$(VERSION) --no-cache .

##@ 部署命令

ifndef ignore-not-found
  ignore-not-found = false
endif

.PHONY: install
install: manifests ## 下发 crd 到 ~/.kube/config 指定的 Kubernetes 集群
	$(KUSTOMIZE) build config/crd | kubectl apply -f -

.PHONY: uninstall
uninstall: manifests ## 从 ~/.kube/config 指定的 Kubernetes 集群中卸载 crd，可指定 ignore-not-found=true 以忽略资源不存在的错误
	$(KUSTOMIZE) build config/crd | kubectl delete --ignore-not-found=$(ignore-not-found) -f -

.PHONY: deploy
deploy: manifests ## 部署 controller 到 ~/.kube/config 指定的 Kubernetes 集群
	cd config/manager && $(KUSTOMIZE) edit set image controller=${IMG}
	$(KUSTOMIZE) build config/default | kubectl apply -f -

.PHONY: undeploy
undeploy: ## 从 ~/.kube/config 指定的 Kubernetes 集群中卸载 controller，可指定 ignore-not-found=true 以忽略资源不存在的错误
	$(KUSTOMIZE) build config/default | kubectl delete --ignore-not-found=$(ignore-not-found) -f -

.PHONY: dockerconfigjson
dockerconfigjson: ## 读取 dockerconfigjson 写入到对应文件中，用于部署时向 controller Deployment 中添加 imagePullSecrets，需指定 DOCKER_CONFIG_JSON 参数
	echo ${DOCKER_CONFIG_JSON} | python3 -m base64 -d > ./config/manager/.dockerconfigjson

##@ 构建依赖项

## Location to install dependencies to
LOCALBIN ?= $(shell pwd)/bin
$(LOCALBIN):
	mkdir -p $(LOCALBIN)

## Tool Binaries
KUSTOMIZE ?= $(LOCALBIN)/kustomize
CONTROLLER_GEN ?= $(LOCALBIN)/controller-gen
ENVTEST ?= $(LOCALBIN)/setup-envtest
GINKGO ?= $(LOCALBIN)/ginkgo
GOLINES ?= $(LOCALBIN)/golines
GOFUMPT ?= $(LOCALBIN)/gofumpt
GOCILINT ?= $(LOCALBIN)/golangci-lint
HELMIFY ?= $(LOCALBIN)/helmify

## Tool Versions
KUSTOMIZE_VERSION ?= v5.5.0
CONTROLLER_TOOLS_VERSION ?= v0.14.0
GOCILINT_VERSION ?= v1.64.8

KUSTOMIZE_INSTALL_SCRIPT ?= "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh"
.PHONY: kustomize
kustomize: $(KUSTOMIZE) ## 安装 kustomize 二进制
$(KUSTOMIZE): $(LOCALBIN)
	curl -s $(KUSTOMIZE_INSTALL_SCRIPT) | bash -s -- $(subst v,,$(KUSTOMIZE_VERSION)) $(LOCALBIN)

.PHONY: controller-gen
controller-gen: $(CONTROLLER_GEN) ## 安装 controller-gen 二进制
$(CONTROLLER_GEN): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-tools/cmd/controller-gen@$(CONTROLLER_TOOLS_VERSION)

.PHONY: envtest
envtest: $(ENVTEST) ## 安装 envtest-setup 二进制
$(ENVTEST): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install sigs.k8s.io/controller-runtime/tools/setup-envtest@v0.0.0-20230216140739-c98506dc3b8e

.PHONY: ginkgo
ginkgo: $(GINKGO) ## 安装 ginkgo 二进制
$(GINKGO): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/onsi/ginkgo/v2/ginkgo@v2.22.2

.PHONY: golines
golines: $(GOLINES) ## 安装 golines 二进制
$(GOLINES): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/segmentio/golines@v0.11.0

.PHONY: gofumpt
gofumpt: $(GOFUMPT) ## 安装 gofumpt 二进制
$(GOFUMPT): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install mvdan.cc/gofumpt@v0.4.0

.PHONY: golangci-lint
golangci-lint: $(GOCILINT) ## 安装 golangci-lint 二进制
$(GOCILINT): $(LOCALBIN)
	test -s $(LOCALBIN)/golangci-lint && $(LOCALBIN)/golangci-lint --version | grep -q $(GOCILINT_VERSION) || \
	GOBIN=$(LOCALBIN) go install github.com/golangci/golangci-lint/cmd/golangci-lint@$(GOCILINT_VERSION)

.PHONY: helmify
helmify: $(HELMIFY) ## 安装 helmify 二进制
$(HELMIFY): $(LOCALBIN)
	GOBIN=$(LOCALBIN) go install github.com/arttor/helmify/cmd/helmify@v0.3.18
