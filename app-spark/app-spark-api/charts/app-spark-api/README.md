# app-spark-api Helm Chart

## local_process 运行方式

当前 Agent 通过 `local_process` 在 API 容器内启动，因此 [Dockerfile](../../Dockerfile)
同时包含 API、Agent 及各自的虚拟环境。构建上下文必须是父目录 `app-spark/`，
不能只使用 API 项目目录。

目前限定单副本、单 worker；升级或配置变更会重建 Pod，造成短暂不可用并中断运行中的会话。

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
