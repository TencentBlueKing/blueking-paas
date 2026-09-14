# repo-server

App-Spark 的 Git 托管组件。每个 Project 的私有仓库、工作分支和仓库范围 token 都落在这里。它和 `app-spark-api`、`agent` 一样是产品的组成部分，不是开发机上的可选依赖。

当前实现是 [forgejo/](forgejo/)（Forgejo 15.0.7 LTS）。

- **本地 / 开发 / 验证**：`cd forgejo && just start`。默认 SQLite + Docker named volume。
- **线上**：使用 Charts 部署，地址：`forgejo/charts/`，推荐使用 MySQL 数据库并做好数据目录持久化。

## 其他

- 个性化设置：private、禁止 push-to-create、分支保护、服务账号无 2FA；
- 本地用 `docker compose exec` 调 Forgejo CLI 建用户，线上的 init Job 会跑同一组 CLI 参数。
