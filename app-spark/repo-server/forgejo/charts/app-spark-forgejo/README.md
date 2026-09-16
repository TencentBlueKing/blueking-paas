# app-spark-forgejo Helm Chart

repo-server 的线上部署：Forgejo 15.0.7 + 外部 MySQL 8 + PVC。本地/开发用同目录上一级的
[compose.yaml](../../compose.yaml)（SQLite + named volume），两者共用同一份初始化代码。

## 为什么要自己构建镜像

官方 `codeberg.org/forgejo/forgejo` 镜像里没有 Python，跑不了 `app_spark_forgejo`。
[../../Dockerfile](../../Dockerfile) 在官方镜像上加发行版 `python3`、用 pip 装 uv，
再 `uv sync --frozen` 装好本包的虚拟环境，与 app-spark-api 镜像的做法一致。
server 和 init Job 共用这一个镜像——线上初始化因此跑的是和 `just init` 完全相同的代码，
而不是在 chart 里另写一遍 shell。

在 `repo-server/forgejo/` 目录执行：

```bash
just image REGISTRY=registry.example.com   # 构建 + 自检，等价于下面两条
docker push registry.example.com/app-spark-forgejo:15.0.7
```

`image.tag` 留空时取 `Chart.appVersion`（即 Forgejo 版本）。同一个 Forgejo 版本重新构建镜像
（例如改了 init 代码）要打带后缀的 tag 并显式设置 `image.tag`，否则无法区分。

升级 Forgejo 版本要同时改三处：`Dockerfile` 的 digest、`compose.yaml` 的 digest、
`Chart.yaml` 的 `appVersion`。升补丁前先看 [15.x 发布说明](https://forgejo.org/releases/15.x/)。

## 部署

按 [values.yaml](values.yaml) 准备 `values-production.yaml`。必填项没填时模板直接报错，
不会部署出一个半残的实例：

| 配置 | 说明 |
| --- | --- |
| `database.host` / `.password` | 外部 MySQL 8.x。chart 不安装数据库，也不支持 SQLite |
| `auth.adminPassword` | 管理员 `app-spark-admin` 的密码 |
| `auth.serviceAccountPassword` | 服务账号 `app-spark-bot` 的密码，app-spark-api 用它签发仓库 token |
| `ingress.host` | 对外主机名，决定 `FORGEJO__server__ROOT_URL` |

数据库需要预先建好库和账号（默认库名 `forgejo`），Forgejo 自己建表。

```bash
helm dependency build charts/app-spark-forgejo
helm upgrade --install app-spark-forgejo charts/app-spark-forgejo \
  --namespace app-spark --create-namespace \
  -f values-production.yaml --wait --wait-for-jobs --timeout 8m
```

两个密码部署后不要再改：`auth.serviceAccountPassword` 变了，等于让 app-spark-api 已签发
的仓库 token 链路失效（签发 token 走的是服务账号的 Basic Auth）。

## 初始化

每次安装/升级创建一个 `<fullname>-init-<revision>` Job，跑 `app-spark-forgejo init`：
等 `/api/healthz` 通过，再创建管理员、服务账号和私有组织 `app-spark`，可重复执行。
`--wait-for-jobs` 会把它的失败暴露成 `helm upgrade` 失败。

```bash
kubectl -n app-spark logs -l app.kubernetes.io/component=init --tail=50
```

这个 Job 不挂业务 PVC：RWO 卷被两个 Pod 同时挂会调度失败，而建账号只写数据库。它用
一个临时 emptyDir 当工作目录，从与 server 相同的 ConfigMap 生成一份一次性 `app.ini`，
所以数据库连接和 server 完全一致。用户名和组织名由 `app_spark_forgejo` 固定，不从 values 配。

## 数据持久化

`/data` 挂 PVC，里面是全部 Project 的 Git 对象、附件，以及首次启动生成的
`SECRET_KEY` / `INTERNAL_TOKEN`。这份数据丢了等于仓库全丢，且无法从数据库重建，
因此本 chart **没有 emptyDir 回退**：要么由 chart 创建 PVC，要么填 `persistence.existingClaim`
指向同 namespace 下已有的 PVC。

chart 创建的 PVC 带 `helm.sh/resource-policy: keep`，`helm uninstall` 不会删它；
同名 release 重新安装会直接复用。确实要清掉时手工删 PVC，或部署时设
`persistence.retainOnDelete=false`（只适合一次性测试环境）。

Forgejo 单进程独占 `/data`，`replicaCount` 只能是 1，更新策略固定 `Recreate`。

## 对外地址与 app-spark-api 的对接

Forgejo 用 `ROOT_URL` 生成 clone URL，所以这个地址必须是**调用方真能解析**的地址：

- `server.rootUrl` 留空时由 `ingress.host` 和 `ingress.tls` 推导；关掉 Ingress 时退回集群内地址。
- 显式填写时必须带 scheme（`http://` 或 `https://`），且不支持裸 IPv6（`http://[::1]:3000`）：
  `DOMAIN` 是从这个地址里截主机名得到的，形状不对模板会直接报错，不会渲染出一份错配置。
- app-spark-api 的 `repoServer.base_url` 填集群内地址（API 自己调 Forgejo），
  `repoServer.clone_url` 填对外地址（写进 Agent 沙箱）。两者不一致是正常形状。
- 沙箱解析不到 `clone_url` 时，故障出现在 Git push 阶段，而不是部署时。

`helm install` 的 NOTES 会按当前 values 打印这两个地址和一份可直接抄的 `repoServer` 配置。

Ingress 走 **ingress-nginx**，整站挂在根路径、不做 rewrite（clone URL 里的路径必须和服务端一致），
并放宽了 `proxy-body-size` 和 `proxy-read-timeout`——git push 的 pack 远超默认的 1m。
按集群配置设置 `ingress.ingressClass`。

## 固化的服务端配置

`ENABLE_PUSH_CREATE_*`、`DEFAULT_PRIVATE`、`DEFAULT_BRANCH`、`DISABLE_REGISTRATION`、
`REQUIRE_SIGNIN_VIEW`、`INSTALL_LOCK`、`DISABLE_SSH` 这些不是调优项，逐条的「作用 / 必要性」
写在 [compose.yaml](../../compose.yaml)，chart 与 Compose 保持一致。`extraConfig` 可以追加其他
Forgejo 配置（例如 `FORGEJO__log__LEVEL`），但改写上述不变量会被模板直接拒绝。

不发 SSH 密钥，只有 Git over HTTP + token 这一个协议，Service 也只暴露 3000。

集群验证方法见 [测试说明](tests/README.md)。
