# 蓝鲸 PaaS3.0 开发者中心代码目录

```
|- bk-PaaS
  |- apiserver
  |- docs  
  |- operator
  |- svc-bkrepo
  |- svc-mysql
  |- svc-otel
  |- svc-rabbitmq
  |- webfe
  |- workloads
```

- apiserver: 提供 REST API，是蓝鲸 PaaS3.0 开发者中心的主要后端服务。
- operator: 蓝鲸 PaaS 平台云原生应用 Operator。
- svc-bkrepo: 对象存储（bk-repo）增强服务。
- svc-mysql: MySQL 增强服务。
- svc-otel: APM 增强服务。
- svc-rabbitmq: RabbitMQ 增强服务。
- webfe: 蓝鲸 PaaS3.0 开发者中心前端模块，是一个基于 Vue.js 构建的单页面应用。
- workloads: 蓝鲸 PaaS3.0 开发者中心的部署控制器，负责和后端 K8S 交互
