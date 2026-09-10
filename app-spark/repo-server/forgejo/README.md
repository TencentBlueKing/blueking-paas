# Forgejo（repo-server 的当前实现）

固定 **Forgejo 15.0.7 LTS**。默认是 **dev 模式**：Compose + SQLite + named volume，用来开发和验收。线上会用同目录 `charts/` 部署。

镜像摘要写在 `compose.yaml` 里。升补丁前先看 [15.x 发布说明](https://forgejo.org/releases/15.x/)。

初始化按「两种部署共用」来写：HTTP 建组织和团队，不假设 SQLite。入口是本目录的 uv 项目
`app-spark-forgejo`（`uv run app-spark-forgejo <subcommand>`）。本地用 `docker compose exec`
调 `forgejo admin user create`；线上 init Job 跑同一组参数。密码优先读环境变量
`FORGEJO_ADMIN_PASSWORD` / `FORGEJO_SERVICE_ACCOUNT_PASSWORD`（chart 注入 Secret），没有时才在
`secrets/` 里生成（gitignore）。

## 地址

| 调用方 | 地址 |
| --- | --- |
| 宿主机上的 API、浏览器、git CLI | `http://127.0.0.1:3000`（端口可由 `FORGEJO_HTTP_PORT` 改） |
| 同一份 Compose 网络里的容器 | `http://server:3000` |
| 别的网络里的 Agent 沙箱 | 需要把本服务接到那个网络，或把 `clone_url` 配成沙箱真能解析的主机名 |

Agent 镜像里写 `http://localhost:3000` 只会打到沙箱自己。

## 入口

在本目录执行（第一次会 `uv sync`，Python 锁在 `.python-version` / `uv.lock`）：

```bash
just start    # 启动、等待就绪、初始化（保留开发数据卷）
just ready    # uv run app-spark-forgejo ready
just init     # uv run app-spark-forgejo init
just logs
just verify   # uv run app-spark-forgejo verify
just stop     # 停止容器，开发数据卷保留
```

测试用的临时实例与开发卷分开：

```bash
just test-up       # 默认端口 3001，独立 Compose 项目、数据卷和 secrets/test
just test-verify
just test-clean    # 删掉测试卷；just stop 不会动它
```

对 App-Spark API 的真实 clone/push 由 API 项目驱动，和拉起 Agent 做集成测试同一模式：

```bash
cd ../../app-spark-api
APP_SPARK_FORGEJO_LIVE=1 .venv/bin/pytest tests/api/live_forgejo
```

未设置 `APP_SPARK_FORGEJO_LIVE=1` 时该目录不会被收集。一旦设置，测试自己会 `just test-up`；Forgejo 起不来就失败，不会 skip。

## 初始化写什么

`just init` 会：

- 创建管理员 `app-spark-admin` 和专用服务账号 `app-spark-bot`（不启用 2FA）
- 创建私有组织 `app-spark`，并把服务账号加进 Owners
- 本地把密码写到 `secrets/credentials.env`；若环境里已有密码则不写盘
- 本地再写一份 API 配置草稿 `secrets/app-spark-api.yaml`，拷进 `app-spark-api/settings_local.yaml`

重复执行不会再建一遍账号。本地密码只在第一次生成，之后一直复用。

## 固化的服务端不变量

这些不是调优，`just verify` 和 chart 都要保持：

- `ENABLE_PUSH_CREATE_USER` / `ENABLE_PUSH_CREATE_ORG` 关闭
- 默认仓库可见性 `private`，默认分支 `main`
- 关闭公开注册，浏览需要登录
- 工作分支的分支保护（禁止强推、禁止删分支）在建仓时由 API 设置；本目录的 `verify` 用测试仓库先验证服务端会拒绝强推

服务账号不得启用 2FA：Forgejo 对开了 2FA 的用户拒绝用户名/密码的 Git over HTTP，签发 token 的 Basic Auth 也会坏掉。初始化不会给它开 2FA。
