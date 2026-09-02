# App-Spark

App-Spark 是蓝鲸运营系统 PaaS 平台推出的基于自然语言开发 SaaS 的工具，支持开发者使用自然语言来开发蓝鲸 SaaS。

组件：

- app-spark-api：项目主要的后端 API 服务，负责直接处理用户请求。
- agent：沙箱内 Agent，提供 `GET /health` 与 `POST /runs`（AG-UI over SSE）。
