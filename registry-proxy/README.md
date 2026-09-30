# registry-proxy

构建镜像代理：云原生应用的 kaniko / CNB 构建容器不再持有平台全局仓库账号，只持有 apiserver 为单次构建签发的**构建 token**。
代理校验 token 与授权后，用自身持有的上游凭证把 OCI Distribution v2 请求转发给真实仓库。

## 设计目标

构建容器里运行的是用户代码（Dockerfile 的 `RUN`、buildpack 脚本），因此把它视为持有构建 token 的攻击者；
而代理持有的上游账号可以读写全平台镜像。整个请求流程围绕三个目标：

- 构建 token 只能做它的声明允许的事；
- 上游凭证不流出代理进程；
- 客户端不能把代理引向配置之外的主机或路径。

## 请求处理流程

```
构建容器 ──HTTPS──▶ registry-proxy ──▶ 上游仓库（Harbor / registry:2 ...）
                     │
                     ├─ 0. 路由解析：解析路由类型、仓库、动作；路径含 % 视为未知路由
                     ├─ 1. 鉴权：校验构建 token（EdDSA / JWKS）                      → 401
                     ├─ 2. /v2/ 探活：未认证返回 Basic 质询，已认证返回 {}，不转发上游
                     ├─ 3. 授权：按固定规则判定，默认拒绝                            → 403 / 404
                     ├─ 4. 纵深防御：DELETE、非法路径、未配置的上游永不转发；越权 mount 降级为普通上传
                     ├─ 5. 目标解析：主机取自配置，按代理计算的 scope 换取并缓存上游 Authorization  → 502
                     ├─ 6. 转发：请求头白名单、401 作废重试、响应头清理、Location 改写与上传会话签名、流式回传
                     └─ 7. 审计与指标：每个请求一行 JSON 审计日志
```

### 0. 路由解析

- **行为**：从路径解析出路由类型（manifest / blob / upload / tags / ping）、客户端视角的仓库（`<别名>/<上游仓库路径>`）、
  所需动作（pull / push）、引用、上传会话 token 和 mount 的 `from`，供授权、转发和审计共用。路径中出现 `%` 时直接视为未知路由。
- **目的**：合法的仓库名、tag、digest 都不需要转义。拒绝 `%2F`、`%2e%2e` 这类编码，
  避免「授权看到的路径」与「转发出去的路径」不一致，出现按 A 仓库授权、实际访问 B 仓库的情况。

### 1. 鉴权：校验构建 token

- **行为**：从 Basic 认证的密码段（忽略用户名）或 Bearer 中取出 token，只接受 `EdDSA` 签名并按 `kid` 选公钥；
  校验 `iss`、`aud`（本集群）、`exp`（必填）、`iat`，允许 30 秒时钟偏差，并校验 `ver`、`sub`、`jti` 与 `push` 条目格式。
  失败返回 401，带 `WWW-Authenticate: Basic realm="bkpaas-registry-proxy"`，错误信息带 `bkpaas-registry-proxy: token_*` 标记。
- **目的**：

  | 措施 | 防范的问题 |
  |------|-----------|
  | 只接受 `EdDSA` | 算法混淆：把公钥当作 HS256 密钥伪造签名，或用 `alg: none` 绕过签名 |
  | 校验 `aud` | 其他集群签发的 token 在本集群的代理上重放 |
  | `exp` 必填 | 泄露的 token 长期可用 |
  | 固定的错误标记 | apiserver 据此把构建失败归类为「镜像凭证不可用」 |

### 2. `/v2/` 探活

- **行为**：未认证的请求在第 1 步拿到 401 和 Basic 质询；认证通过后返回 200 `{}`。`/v2/` 永远不转发给上游；
  未带 token 的探活属于正常流程，审计中不记为拒绝。
- **目的**：Docker 客户端（kaniko、lifecycle）先访问 `/v2/`，收到质询后才带上凭证，未认证就返回 200 会导致后续请求不带 token。
  质询始终指向代理自己，不会把客户端引向上游的 token 服务。

### 3. 授权

- **行为**：按以下顺序判定，默认拒绝：
  1. `DELETE` 返回 403，未知路由返回 404；
  2. 别名未配置返回 403；
  3. 推送：仓库必须精确命中 `push` 中的一条；推送 manifest 时 tag 必须在允许列表中，只有 `"*"` 才允许按 digest 推送；
  4. 拉取：命中 `push` 的仓库放行 → 命中 `pull_deny` 拒绝 → 命中 `pull` 放行 → 其余拒绝；
  5. mount：来源不可读或跨上游时，标记为需要降级。
- **目的**：
  - 推送按仓库和 tag 精确授权，防止构建覆盖其他应用的镜像或本应用的其他 tag（例如 `latest`）；
  - `pull_deny` 覆盖整个平台命名空间，防止读取其他应用的镜像；
  - `push` 授权优先于 `pull_deny`，本应用的产物与缓存仓库也在该命名空间下，这样才能读取构建缓存；
  - 有的上游签发的 token 不按 scope 限权，这一步就是那里唯一的访问控制。

### 4. 纵深防御

- **行为**：授权钩子放行后，再做一遍不依赖钩子实现的检查：
  - `DELETE` 一律返回 403；
  - 仓库名、tag、digest 必须符合 OCI 规范，`manifests/..` 这类请求返回 404；
  - 别名必须在配置中；
  - 以下 mount 去掉 `mount` / `from`，降级为普通上传：
    - 跨上游：客户端把所有上游视为同一个 registry，会拿 A 上游的路径去 B 上游 mount；
    - 来源不可读：mount 相当于不经过拉取就复制数据，放行即绕过 `pull_deny`；
    - 缺少 `from`：部分 registry 理解为「从凭证可读的任意仓库挂载」，而代理账号可读全平台；
  - 保留的 mount 去掉 `from` 中的别名段后转发。
- **目的**：即使授权钩子被替换为全部放行或判定逻辑有缺陷，删除镜像、访问未配置的上游、借 mount 越权读取这三类操作也不会发生
  （`TestDefenseInDepthWithPermissiveAuthorizer` 用全部放行的钩子验证）。

### 5. 目标解析与上游鉴权

- **行为**：
  - 上游地址：主机只取自该别名在配置中的 URL；普通请求的路径为去掉别名段后的原路径，续传请求的路径取自签名会话（见 6.4）。
  - scope：按路由计算，例如 `repository:bkpaas/app:pull,push`；保留的 mount 再加上来源仓库的 `pull`。
  - 上游 Authorization：先请求上游 `/v2/` 获取认证方式（缓存 10 分钟）；Bearer 方式带代理凭证去 realm 换 token，
    Basic 方式直接使用凭证。按「上游 + scope」缓存，在 `expires_in` 的 90% 处过期，同一 scope 的并发请求只换一次 token。
  - 失败返回 502，拒绝原因为 `upstream_auth_failed` 或 `upstream_unreachable`，错误信息不含凭证与上游响应体。
- **目的**：

  | 措施 | 目的 |
  |------|------|
  | 主机只取自配置 | 防 SSRF：客户端无法让代理带着上游凭证访问其他主机 |
  | 发请求前按路由计算 scope | 上传请求的请求体是流式转发的，被上游 401 打回后无法重放，因此不能等质询再换 token；上游 token 的权限范围只由授权结果决定，不采用上游质询中的 scope（有的上游返回与仓库无关的固定值） |
  | 缓存 Authorization | 一次推送有几十到上百次上游请求，换一次 token 约 200ms，不缓存会显著拖慢构建并压垮上游 token 服务 |
  | 上游为 HTTPS 时拒绝明文 realm | 防止代理凭证以 Basic 方式明文发出 |
  | 不支持 `identitytoken`，凭证打印为 `<redacted>` | 避免把 OAuth2 refresh token 误当 Bearer 使用；防止凭证误入日志 |

### 6. 转发与响应改写

**6.1 请求头白名单**：只转发 `Accept`、`Content-Type`、`Content-Range`、`Range`、`User-Agent` 等 OCI 客户端需要的头，
`Authorization` 由代理设置。构建 token、客户端的 `Cookie`、`X-Forwarded-For` 与逐跳头都不会到达上游。

**6.2 发送与 401 重试**：

- 请求体流式转发，保留客户端声明的 `Content-Length`，避免改为 chunked 上传；有请求体时带 `Expect: 100-continue`，
  上游提前拒绝时不必传完 GB 级数据。
- 上游返回 401 时作废对应 scope 的缓存：无请求体的请求（GET、HEAD、开始上传等）重新鉴权后重试一次；
  有请求体的请求无法重放，由下一个请求重新鉴权。上游提前作废 token 时客户端无感知。
- 上游 401 最终改为 502 返回：它说明代理自己的凭证有问题，透传会让客户端误以为构建 token 失效。

**6.3 响应头清理**：

| 删除 / 改写 | 原因 |
|------------|------|
| `WWW-Authenticate` | 上游质询指向上游 token 服务，客户端照做会带着构建 token 直连上游，既暴露 token 也绕开代理 |
| `Set-Cookie` | 上游可能返回代理账号的会话 Cookie（例如 Harbor 的 `sid`），透传等于把上游凭证交给构建 |
| 逐跳头（`Connection`、`Keep-Alive` 等） | 实测 Harbor 返回 `Keep-Alive`，HTTP/2 客户端收到后报协议错误 |
| `Link`（tags/list 分页） | 其中的上游路径改写为带别名段的代理路径 |

**6.4 `Location` 改写与上传会话签名**：

- 开始上传或续传时，上游返回的续传地址与客户端视角的仓库、过期时间一起做 HMAC-SHA256 签名（带签名域），
  客户端拿到的是 `/v2/<仓库>/blobs/uploads/<会话 token>`。续传时先验签，并要求会话所属仓库与请求路径一致，
  否则返回 403 `invalid_upload_session`。目的：
  - 上传会话只能在创建它的仓库下使用。有的上游不做这层绑定，代理签名是唯一的约束（见 `docs/forwarding-design.md` 2.1 节）；
  - 代理不保存会话状态，多副本共享密钥即可续传；
  - 不向构建暴露上游的上传 ID 与 `_state`。
- 续传地址不在上游自身主机上时返回 502，不签发会话，代理只把请求发往配置中的主机。
- 指向上游 `/v2/` 的地址改写为代理的相对地址并补回别名段，保证客户端的下一个请求仍经过代理。
- 指向其他主机的 307（例如 Harbor 重定向到对象存储的预签名地址）原样返回。代理不跟随重定向，
  因此不会把凭证发给存储服务，也不承担下载流量。

**6.5 流式回传**：用池化的 64 KiB 缓冲区边读边写，内存不随 blob 大小增长（转发 2 GiB 时内存增量约 5 MiB）。
客户端或上游中途断开时复制随即结束，上游连接随之释放。

### 7. 审计与指标

- **行为**：每个请求（包括被拒绝和未认证的）输出一行 JSON 审计日志，字段包括构建 ID、`jti`、应用、仓库、上游、引用、
  状态码、字节数、耗时、重定向目标主机与拒绝原因；同时更新 Prometheus 指标。
- **目的**：
  - 满足「谁 pull / push 了哪张镜像」的追溯，每条记录都能关联到具体的构建；
  - 审计不能成为泄露渠道：不记录 `Authorization` 与 token，不记录上传会话 token，307 只记目标主机而不记预签名 URL；
  - 有的上游按仓库路径的前两段共享 blob，已知 digest 时可以跨应用读取。审计里记下的 blob digest 是这件事的补偿措施。

各项防护的测试在 `pkg/proxy/server_test.go`，用例名与防护对应；与审计风险项的对照见 `docs/forwarding-design.md` 第 3 节。

## 代码结构

一次请求的调用链为 `ServeHTTP` → `handle`（第 0～4 步）→ `forward`（第 5～6 步）→ `finish`（第 7 步），均在 `pkg/proxy/server.go`。

| 目录 | 作用 | 对应流程 |
|------|------|---------|
| `cmd/registry-proxy` | 入口：加载配置、JWKS、上游凭证与会话密钥，HTTPS 监听、管理端口（健康检查与指标）、优雅退出 | 启动 |
| `pkg/config` | 配置加载与校验。影响安全或转发目标的字段没有缺省值，缺失时拒绝启动 | 启动 |
| `pkg/oci` | 路由解析与路径校验；拒绝原因常量与 OCI 错误响应（含 401 质询） | 0、4；各步的错误响应 |
| `pkg/buildtoken` | 构建 token（JWT）与 JWKS 校验，移植自参考实现 | 1 |
| `pkg/policy` | 授权判定，移植自参考实现 | 3 |
| `pkg/authz` | 把 `buildtoken`、`policy` 接入代理的鉴权与授权钩子 | 1、3 |
| `pkg/upstream` | 别名推导、上游凭证加载、每个上游独立的连接配置、按「上游 + scope」缓存的 Bearer / Basic 鉴权 | 5 |
| `pkg/proxy` | 协议转发层：钩子接口与主流程、纵深防御、上游发送与 401 重试、响应头清理、`Location` 改写、上传会话签名、审计与指标 | 2、4、5、6、7 |
| `docs/forwarding-design.md` | 转发层选型（不依赖 ociproxy 的原因）、安全设计与上游行为实测 | — |
| `hack/` | 集成测试、e2e 脚本、上游行为探测、压测与 token 工具 | — |

`pkg/proxy` 内部按文件划分：`hooks.go`（鉴权、授权、审计钩子接口）、`server.go`（主流程、纵深防御、目标解析、`Location` 改写）、
`transport.go`（上游发送与 401 重试）、`writer.go`（响应头清理与字节统计）、`session.go`（上传会话签名）、
`audit.go`、`metrics.go`。

## 配置

见 [`config.example.yaml`](config.example.yaml)。必需的输入：

| 输入 | 配置项 | 说明 |
|------|--------|------|
| TLS 证书 | `tls.cert_file` / `tls.key_file` | 代理必须提供 HTTPS；`plain_http` 仅用于本地测试 |
| 构建 token 公钥 | `jwks_file`、`audience` | JWKS 由 apiserver 管理命令 `export_build_token_jwks` 导出 |
| 上游凭证 | `upstream_docker_config_file` | docker config.json 格式，只存在于代理进程内 |
| 上游别名 | `upstreams[]` | `alias` 必须等于按 URL 主机名推导的值，启动时校验 |
| 上传会话密钥 | `upload_session.key_file` | 不少于 32 字节，多副本必须相同；轮换时旧密钥放在 `previous_key_file` |

输出：

- `:8443`：构建容器访问的 HTTPS 入口；
- `:9090`：`/healthz`（存活）、`/readyz`（就绪，退出时先变为未就绪）、`/metrics`（Prometheus）；
- 标准输出：每个请求一行 JSON 审计日志；标准错误：运行日志。

主要指标（前缀 `bkpaas_registry_proxy_`）：`requests_total{route,method,code}`、`request_duration_seconds{route}`、
`upstream_request_duration_seconds{upstream,route}`、`transferred_bytes_total{upstream,direction}`、
`upstream_auth_total{upstream,result}`、`denied_total{deny}`、`audit_write_failures_total`。

## 开发与验证

```bash
make test         # 单元测试（-race）
make lint         # golangci-lint
make integration  # 基于本地 registry:2 的集成测试：多副本分块上传、mount 与跨上游 mount 降级、digest 一致性
make bench        # 2GiB blob 流式转发的内存与吞吐、HEAD 附加延迟（代理绑定单核、GOMAXPROCS=1）
make e2e-local    # 本地 registry:2 + kaniko v1.24.0 的端到端构建与负面用例
```

在真实上游上验证时，复制 `hack/e2e/env.example.sh` 为 `hack/e2e/env.sh` 并填写测试仓库，然后执行：

```bash
bash hack/e2e/00-build.sh
bash hack/e2e/20-kaniko.sh            # 经代理构建，digest 与直连上游一致
bash hack/e2e/30-negative.sh HARBOR   # 认证、越权与凭证不外泄
```
