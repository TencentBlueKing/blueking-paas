# app-spark-api Helm Chart

## local_process 运行方式

当前 Agent 通过 `local_process` 在 API 容器内启动，因此 [Dockerfile](../../Dockerfile)
同时包含 API、Agent 及各自的虚拟环境。构建上下文必须是父目录 `app-spark/`，
不能只使用 API 项目目录。

目前限定单副本、单 worker；升级或配置变更会重建 Pod，造成短暂不可用并中断运行中的会话。

## e2b 运行方式

`agent.runtimeProvider: e2b` 时，每个会话在 e2b 沙箱里运行 Agent，沙箱模板由
[agent 镜像](../../../agent/README.md) 添加而来。按 [values.yaml](values.yaml) 中注释的 e2b 示例填写
`agent.runtimeProviderConfig`，只写 e2b 的字段即可：Helm 会把 values.yaml 里 local_process 的默认字段合并进来，
Chart 在 e2b 模式下会自动去掉它们。`api_key`、`api_url`、`callback_base_url`、`template` 缺任何一项，渲染直接失败，
不会等到第一个会话才报错。

e2b 模式可以多副本（`replicaCount` 大于 1），前提是 `agent.contextStorage.backend` 为 `bk_repo`。其余后端
（包括默认的 `host_tmp_path`）只存在单个 Pod 内，会话换到别的副本冷启动时读不回上下文，Chart 渲染时直接拒绝。
改用 `bk_repo` 时 `root` 要一起改成通用仓库名：只改 `backend`，Helm 会把默认的路径合并进来，Chart 会拒绝以 `/` 开头的 `root`。

e2b 模式按 RollingUpdate 升级：API 进程退出不会停掉沙箱，新旧 Pod 可以同时在线。上下文存在 `bk_repo` 时，
API Pod 不往 `/data/app-spark` 写东西，不需要 `persistence`；单副本仍用 `host_tmp_path` 时上下文写在这里。
设置了 `existingClaim` 时，它必须是 ReadWriteMany：滚动升级和多副本都会让两个 Pod 同时挂这个卷，
ReadWriteOnce 的卷挂不到别的节点上，新 Pod 会一直 Pending。

## 部署

以下命令在 app-spark-api 项目目录执行：

```bash
docker build -f Dockerfile -t registry.example.com/app-spark-api:0.1.0 ..
docker push registry.example.com/app-spark-api:0.1.0
```

按 [values.yaml](values.yaml) 准备 `values-production.yaml`，填写实际环境配置。
可选业务配置未定义或为 `null` 时沿用应用默认值；显式的 `false`、`0` 和空值仍会生效。

```bash
helm dependency build charts/app-spark-api
helm upgrade --install app-spark-api charts/app-spark-api \
  --namespace app-spark --create-namespace \
  -f values-production.yaml --wait --wait-for-jobs --timeout 6m
```

Ingress 依赖 **ingress-nginx**，使用正则路径 `/api-svc(/|$)(.*)` 和重写目标 `/$2`，
转发时去掉外部 `/api-svc` 前缀。按集群配置设置 `ingress.ingressClass`。

前端服务可在同一域名单独配置 `/` 的 Ingress，无需添加上述重写注解。

## 数据持久化

正式使用时设置 `persistence.existingClaim`，挂载已有 PVC。
默认的 `emptyDir` 会在 Pod 删除后丢失 workspace 和本地上下文；数据库中的会话记录不能替代这些文件。
自定义本地存储路径应位于 `/data/app-spark` 下，才能使用该挂载。

集群验证方法见 [测试说明](tests/README.md)。
