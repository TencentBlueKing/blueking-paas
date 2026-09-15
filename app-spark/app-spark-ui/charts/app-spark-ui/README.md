# App Spark UI Chart

使用本项目 `Dockerfile.prod` 构建的静态 UI 镜像。

从 UI 项目目录执行：

```bash
helm dependency build charts/app-spark-ui
helm lint charts/app-spark-ui --strict -f values.prod.yaml
helm template app-spark-ui charts/app-spark-ui -f values.prod.yaml
helm upgrade --install app-spark-ui charts/app-spark-ui \
  --namespace app-spark --create-namespace -f values.prod.yaml --wait --timeout 5m
```

`values.prod.yaml` 示例及镜像构建、API 路由、TLS、子路径、验收和回滚说明见
[生产部署文档](../../docs/PRODUCTION_DEPLOYMENT.md)。发布前必须覆盖镜像仓库、标签、域名和
`env.BK_LOGIN_URL`；默认 values 用于展示结构，空登录地址会使容器启动失败。
