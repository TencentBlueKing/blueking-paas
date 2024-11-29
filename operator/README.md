# bkpaas-app-operator

蓝鲸 PaaS 平台云原生应用 K8S Operator（k8s >= 1.19）。

## 开发指南

安装 manifest 生成/管理工具

    $ make controller-gen
    $ make kustomize

安装 ginkgo 命令行工具：

    $ make ginkgo

安装格式化 & lint 工具：

    $ make golines 
    $ make gofumpt
    $ make golangci-lint

执行 fmt & lint

    $ make fmt
    $ make lint

执行单元测试：

    $ make test

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

    $ export ENABLE_WEBHOOKS=false

### 部署至测试用 Kubernetes 集群

如果你能用 kubectl 命令直接访问到一个测试用 Kubernetes 集群，那么你就可以将 operator 服务部署到集群中，进行任何功能测试。

首先，在集群内安装 cert-manager 服务，参考文档 ["Installation"](https://cert-manager.io/docs/installation/) 或直接运行以下命令：

    $ kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.8.2/cert-manager.yaml

生成拉取私有 Registry 所需的 dockerconfig 文件（可选，仅当需将镜像推送到私有 registry 时使用，DOCKER_CONFIG_JSON 为 base64 字符串）：

    $ make dockerconfigjson DOCKER_CONFIG_JSON="eyJhdXRo...=="

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

### 项目 Error 使用指南

由于项目支持接入 sentry 以及时监控并报告调和循环中的错误，因此要求 error 均携带堆栈信息。

目前的解决方案是基于 `github.com/pkg/errors` 的能力，对 stderr 进行包装。

参考使用方式：
- 第三方包返回的错误，如 `err := json.Unmarshal(...)`， 使用 `errors.WithStack()` 以携带堆栈信息
- sentinel error，即 `var err = errors.New("xxx")`，在实际使用处也使用 `errors.WithStack()` 包装
- 新建的错误，应该使用 `errors.Errorf("xxx: %s", val)`，不应使用 `fmt.Errorf("xxx: %s", val)`
- 需要对调用方返回的错误进行包装，携带额外的信息，应该使用 `errors.Wrap / errors.Wrapf` 而非 `fmt.Errorf + %w`

注意：
- 与 k8s 交互返回的错误，如 `r.Client.Get()`, `r.Client.Status().Update()` 等在 client 中封装过，无需添加 `errors.WithStack`

## 目录说明

```text
./operator
├── Dockerfile
├── Makefile
├── PROJECT
├── README.md
├── api              // CRD 结构定义
│   └── v1alpha1
│       └── ...
├── config
│   ├── certmanager  // 证书管理配置
│   │   └── ...
│   ├── crd          // CRD 定义配置
│   │   └── ...
│   ├── default      // controller patch 等配置
│   │   └── ...
│   ├── manager      // controller 基础配置
│   │   └── ...
│   ├── rbac         // CRD 权限控制相关
│   │   └── ...
│   ├── samples      // CRD 示例配置
│   │   └── ...
│   └── webhook      // 校验等 webhook 配置
│       └── ...
├── controllers      // 各 CRD controller 定义
│   └── ...
├── go.mod
├── go.sum
├── hack
│   └── ...
├── main.go
└── pkg
    ├── config             // Operator 配置信息
    │   └── ...
    ├── controllers
    │   ├── reconcilers    // 调和循环逻辑
    │   │   └── ...
    │   └── resources      // 资源管理，将 CRD 配置转换成基础 k8s 资源
    │       └── ...
    ├── health             // 组件健康状态
    │   └── ...
    ├── kubeutil           // k8s 资源操作相关工具
    │   └── ...
    ├── metrics            // 服务指标（prometheus）
    │   └── ...
    ├── platform
    │   └── applications // 蓝鲸应用交互相关
    │       └── ...
    ├── testing            // 单元测试相关
    │       └── ...
    └── utils
        ├── hash           // 配置 Hash 相关工具
        │   └── ...
        ├── quota          // 资源配额类工具
        │   └── ...
        └── stringx        // 字符串相关工具
            └── ...
```

## 更多开发指南

### 选择日志级别

在打印 Info 日志时，调用 `.V(...)` 方法可设置日志可视级别：

```go
package main

import logf "sigs.k8s.io/controller-runtime/pkg/log"

func main() {
    log := logf.FromContext(ctx)
    log.V(1).Info("handling revision reconciliation")
}
```

推荐使用的日志级别如下：

- `0`：Info 级别. 普通日志，不指定 `V()` 时的默认为该级别
- `1`：Debug 级别. 调试类日志，可能会大量频繁出现，对排查问题有帮助
