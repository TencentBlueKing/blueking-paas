# bkpaas-app-operator

蓝鲸 PaaS 平台云原生应用 Operator。

## 部署说明

K8S 集群版本要求: **>=1.17**

### 部署步骤
1. (可选) 安装 cert-manager

cert-manager 用于签发 webhooks 需要的证书, 如不希望安装 cert-manager, 则需要自行管理 https 证书, 可根据此[文档](https://cert-manager.io/docs/installation/supported-releases/)选择需要安装的 cert-manager 版本

2. 创建命名空间

```bash
kubectl create ns bkpaas-app-operator-system
```

3. helm install

```bash
helm install bkpaas-app-operator paasv3/bkpaas-app-operator -n bkpaas-app-operator-system -f values.yaml
```

其中: 
- paasv3/bkpaas-app-operator 维护在仓库 [helm-deploy] 项目
- values.yaml 维护在仓库 [helm-values] 项目

## 开发指南

安装 ginkgo 命令行工具：

    $ go install -mod=mod github.com/onsi/ginkgo/v2/ginkgo@latest

执行单元测试：

    $ make test

安装格式化 & lint 工具：

    $ go install github.com/segmentio/golines@latest 
    $ go install mvdan.cc/gofumpt@latest
    $ brew install golangci-lint

执行 fmt & lint

    $ make fmt
    $ make lint

更新 helm-chart

    $ make update-helm-chart HELM_CHART_TARGET_DIR=/tmp/bkpaas-app-operator

注意：需要根据检查到的 diff 结果，手动更新 values.yaml 文件

### 本地开发/调试

下发 CRD 配置到 Kubernetes 集群：

    $ make install

开发环境运行 controller：

    $ make run

从 Kubernetes 集群中卸载 CRD：

    $ make uninstall

若开发/联调时不启用 Webhook 服务，请参考以下命令配置环境变量：

    $ export ENABLE_WEBHOOKS=true

### 部署至测试用 Kubernetes 集群

如果你能用 kubectl 命令直接访问到一个测试用 Kubernetes 集群，那么你就可以将
operator 服务部署到集群中，进行任何功能测试。

首先，在集群内安装 cert-manager 服务，参考文档 ["Installation"](https://cert-manager.io/docs/installation/)
或直接运行以下命令：

    $ kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.8.2/cert-manager.yaml

生成拉取私有 Registry 所需的 dockerconfig 文件（可选，仅当需将镜像推送到私有 registry 时使用）：

    $ make dockerconfigjson

构建容器镜像：

    # 可选参数 IMG，当不传递任何参数时，目标镜像名默认为 controller:latest
    $ make docker-build

    # 指定 IMG，构建并推送的示例
    $ make docker-build docker-push IMG=<some-registry>/bkpaas-app-operator:tag

    # 若集群为 minikube，还需执行以下命令将镜像加载至 minikube 虚拟机中
    $ minikube image load <IMAGE NAME>

最后，部署 controller 至集群：

    $ make deploy

    # 指定 IMG 部署的示例
    $ make deploy IMG=<some-registry>/bkpaas-app-operator:tag

> 注意：Operator 的默认镜像拉取策略为 Always。如你未将镜像推送至任意 Registry 中，请用以下命令，将 deployment 的
> imagePullPolicy 修改为 Never 或 IfNotPresent，否则服务将无法正常启动。
> 
>  `kubectl -n bkpaas-app-operator-system edit $(kubectl -n bkpaas-app-operator-system get deploy -o name)`

从集群中卸载 controller：

    $ make undeploy

> **NOTE:** 执行 `make help` 命令以查看更多的 make 命令说明
> 
> 更多 Operator 开发信息请参考 [Kubebuilder Documentation](https://book.kubebuilder.io/introduction.html)

## 目录说明

```text
./operator
├── Dockerfile
├── Makefile
├── PROJECT
├── README.md
├── api // CRD 结构定义
│   └── v1alpha1
│       └── ...
├── config
│   ├── certmanager // 证书管理配置
│   │   └── ...
│   ├── crd // CRD 定义配置
│   │   └── ...
│   ├── default // controller patch 等配置
│   │   └── ...
│   ├── manager // controller 基础配置
│   │   └── ...
│   ├── rbac // CRD 权限控制相关
│   │   └── ...
│   ├── samples // CRD 示例配置
│   │   └── ...
│   └── webhook // 校验等 webhook 配置
│       └── ...
├── controllers // 各 CRD controller 定义
│   └── ...
├── go.mod
├── go.sum
├── hack
│   └── ...
├── main.go
└── pkg
    ├── config // Operator 配置信息
    │   └── ...
    ├── controllers
    │   ├── reconcilers // 调和循环逻辑
    │   │   └── ...
    │   └── resources // 资源管理，将 CRD 配置转换成基础 k8s 资源
    │       └── ...
    ├── platform
    │   ├── applications // 蓝鲸应用交互相关
    │   │   └── ...
    │   └── external // 远程服务相关（增强服务等）
    │       └── ...
    └── utils
        ├── hash // 配置 Hash 相关工具
        │   └── ...
        └── quota // 资源配额类工具
            └── ...
```
