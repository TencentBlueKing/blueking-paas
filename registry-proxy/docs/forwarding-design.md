# 转发层选型与安全设计

转发层原计划引入 PoC 使用的 [github.com/adiom-data/ociproxy](https://github.com/adiom-data/ociproxy)，
固定版本并完成代码审计。审计完成后决定**不依赖该库**，转发层基于 Go 标准库自行实现。本文记录选型结论，
以及自研实现如何覆盖审计中发现的每个风险项。

## 1. 选型结论（2026-09-29）

| 候选 | 结论 | 原因 |
|------|------|------|
| ociproxy `v0.0.0-20260623212025-e462979bc350` | 不采用 | 只有 2026-06 的一个伪版本，0 star、0 fork，无维护者与安全响应渠道。审计的 10 个风险项中，大部分需要在库外绕开（见第 3 节），库实际只剩上传会话签名、`Location` 改写与上游请求构造约 300 行的价值；它还与 `pkg/oci` 重复解析路由且规则不一致（拒绝 OCI 规范允许的 `a__b`、`a--b` 仓库名） |
| distribution pull-through、Harbor 代理缓存、zot sync、Dragonfly / spegel | 不适用 | 只支持拉取，不支持推送 |
| go-containerregistry `pkg/v1/remote/transport` | 不适用 | 客户端库而非代理；上游返回 401 时会把质询中的 scope 合并并前置（`bearer.go`），与「不使用上游质询中的 scope」冲突（原因见 2.2） |
| Envoy / nginx + 外部鉴权服务 | 不采用 | 上传会话绑定、`Location` 改写、mount 降级都需要 Lua / njs 实现，并增加一套需要部署运维的组件 |
| artifact-gateway、alauda connectors 等 | 不适用 | 完整产品而非可嵌入的库，且以拉取为主 |

自研后的依赖只有 golang-jwt（token 校验）、prometheus client（指标）、yaml 与 x/sync（singleflight），均为成熟库。

## 2. 转发层设计

实现位于 `pkg/proxy`：`server.go`（处理流程、上游地址、`Location` 改写）、`session.go`（上传会话）、
`transport.go`（发送与 401 重试）、`writer.go`（响应头清理）。

**上游地址**只由配置决定：普通请求为「上游根地址 + 去掉别名段的路径」；续传请求为「上游根地址 + 会话中记录的上游路径与查询串」。
主机名永远取自配置，客户端无法把请求引向其他主机。

**上传会话**（`session.go`）：上游返回的续传地址（路径与查询串，例如 `/v2/<仓库>/blobs/uploads/<id>?_state=...`）
连同客户端视角的仓库与过期时刻编码为 JSON，以 HMAC-SHA256 签名（带固定的签名域前缀）后作为客户端 `Location` 的最后一段。

- 会话绑定客户端仓库，拿到其他仓库使用时返回 403 `invalid_upload_session`；
- 过期时刻在会话开始时确定，续传时不延长（`upload_session.ttl`，缺省 1 小时，覆盖构建超时 + 300 秒）；
- 代理不保存会话状态，副本间共享密钥即可续传；`previous_key_file` 用于密钥轮换；
- 与 ociproxy 只记录上传 ID 再拼接路径不同，这里记录上游给出的完整续传地址，不依赖各家 registry 的路径布局；
- 上游给出的续传地址不在上游自身主机上时直接返回 502，不签发会话。

**`Location` 改写**：上传会话地址签名为会话 token；指向上游 `/v2/` 的地址改写为代理的相对地址并补回别名段；
指向其他主机的地址（例如 Harbor 307 到对象存储的预签名地址）原样保留，由客户端直连。

**流式转发**：客户端请求体直接作为上游请求体，并保留客户端声明的 `Content-Length`；响应体经 64KiB 的池化缓冲区流式写回。
客户端或上游中途断开时复制结束，上游响应体随即关闭，请求 context 取消后上游连接释放。

### 2.1 为什么由代理签名上传会话（实测，2026-09-29）

另一种做法是不签名，直接透传上游的续传地址（只补回别名段），由上游自己把会话绑定到仓库。
`hack/e2e/upload-session-probe.py` 用代理持有的上游凭证直连上游验证了这一前提：

| 检查项 | Harbor | 直接返回 blob 的上游 |
|--------|--------|----------------------|
| 续传地址格式 | 同一主机，`/v2/<仓库>/blobs/uploads/<id>`，带 `_state` | 同一主机，`/v2/<仓库>/blobs/uploads/<id>`，无查询参数 |
| A 仓库的会话拿到 B 仓库路径下续传、完成 | 404 / 405，拒绝 | 202 / 201，**接受** |
| 伪造上传 ID | 404 | 400 |
| 去掉或篡改 `_state` | 404 | 202（不使用 `_state`） |

结论：后一类上游不把上传会话绑定到仓库，透传方案下会话与仓库的绑定只剩「上传 ID 不可猜测」这一层，因此**保留代理签名**。

同一测试还发现这类上游的 blob 按镜像路径的前两段共享：上传到 `group/project/app` 的 blob，
可以通过从未推送过的 `group/project/<任意名>` 路径 GET 到原内容；不同的前两段之间不共享，Harbor 则按镜像仓库隔离。
因此在这类上游上，`pull_deny` 只能挡住其他应用的 manifest，挡不住已知 digest 的 blob：
构建可以经自己有权拉取的仓库路径读取同一前两段下其他应用的层。
这属于授权策略问题，已在《镜像代理授权策略与审计》中作为已接受风险记录（前提、补偿措施与重新评估条件见该文档）。

### 2.2 为什么 scope 由代理按路由计算（实测，2026-09-29）

`hack/e2e/scope-probe.py` 直连上游，记录未认证请求的质询 scope，再用不同 scope 换取的 token 访问两个仓库：

| 检查项 | Harbor | 直接返回 blob 的上游 |
|--------|--------|----------------------|
| `GET /v2/` 的质询 scope | 无 | `repository:*/*/tb:push,pull` |
| 拉 A manifest 的质询 scope | `repository:<A>:pull` | 同上（固定值） |
| 在 B 开始上传的质询 scope | `repository:<B>:push,pull` | 同上（固定值） |
| 从 A mount 到 B 的质询 scope | `repository:<B>:pull,push repository:<A>:pull` | 同上（固定值） |
| 只申请 A 的 pull 换到的 token | `access` 只含 A；拉 A 200、推 A 202、推 B 401 | 无 `access` 声明；拉 A、推 A、推 B 均成功 |
| 申请无关仓库或不申请 scope | 访问 A、B 均 401 | 同上，均成功 |

结论：后一类上游的质询 scope 是与请求无关的固定占位值，但它的 token 本身不按 scope 限权，申请什么 scope 都能用，
所以按质询 scope 申请也能工作；Harbor 的质询 scope 准确（mount 也带上了来源仓库）。不采用质询 scope 是因为：

- 代理在发请求前就能按已通过授权的路由算出 scope，不必先吃一次 401 再换 token，token 缓存也能按「上游 + scope」稳定命中；
- 上游 token 的权限范围由代理的授权结果决定，而不是由上游返回的内容决定，
  两者只会一致或更窄（例如 mount 被降级后不再申请来源仓库的 pull）；
- 固定占位 scope 不是合法仓库名，按它做缓存键会让同一上游所有仓库共用一个条目，
  一旦这类上游开始按 scope 限权就会串权限或失败。

## 3. 审计风险项的覆盖

以下为 ociproxy 审计中发现的风险项，以及自研实现中的对应处理与测试（测试均在 `pkg/proxy`）。

| 风险 | 处理 | 测试 |
|------|------|------|
| 客户端请求头原样转发给上游（含 `Cookie`、逐跳头） | 只转发白名单内的头（`Accept`、`Content-Type`、`Content-Range`、`Range`、`User-Agent` 等），`Authorization` 由代理设置 | `forwards only allowed request headers`、`strips ... upstream challenges` |
| 上游响应头原样透传（`WWW-Authenticate`、`Set-Cookie`、逐跳头） | 删除质询、Cookie 与 RFC 7230 逐跳头；`Link` 分页地址改写回客户端视角。实测 Harbor 返回 `Keep-Alive`，透传会导致 HTTP/2 客户端报协议错误 | `strips ... upstream challenges`、`drops hop-by-hop headers for HTTP/2 clients`、`rewrites the Link header of tags/list` |
| 跨上游 mount 泄露来源路径 | 跨上游、来源不可读、或缺少 `from` 的 mount 去掉 `mount` / `from` 降级为普通上传；缺少 `from` 的 mount 在部分 registry 上表示从凭证可读的任意仓库挂载，而代理账号可读全平台 | `mount downgrades to a plain upload`、`Integration with registry:2` |
| manifest / blob 的 `DELETE` 会被转发 | 授权钩子第一步拒绝；`Server.handle` 再兜底拒绝，授权钩子被替换也不会转发 | `rejected requests never reach upstream`、`Server with a permissive authorizer` |
| 路径穿越与编码分隔符 | 路径含 `%` 时视为未知路由；仓库名、tag、digest 按 OCI 规范校验，`..` 等引用返回 404 | `rejected requests never reach upstream` |
| 上游 401 直接返回 502，不作废缓存、不重试 | 作废对应 scope 的缓存；无请求体的请求重新鉴权后重试一次；仍失败返回 502 `upstream_auth_failed` | `re-authenticates after the upstream revokes its token` |
| 上游鉴权无超时、忽略 `expires_in`、每次重新质询、误用 `identitytoken`、向明文 realm 发送凭证 | `pkg/upstream/auth.go` 自行实现：30 秒超时，按 `expires_in` 的 90% 过期，缓存质询，singleflight 合并并发未命中，拒绝 `identitytoken` 与 HTTPS 上游的明文 realm | `pkg/upstream/auth_test.go` |
| 错误为纯文本，不符合 OCI 错误格式 | 所有代理自身的错误经 `oci.WriteError` 输出 OCI 错误格式与 `bkpaas-registry-proxy: ` 标记 | `assertProxyError` 覆盖的全部用例 |
| 上游请求未设置 `Content-Length`，被改为 chunked 上传 | 按客户端声明的长度转发，无请求体时不发送请求体 | `Integration with registry:2`、`make bench` |
| 自动协商 gzip 会改变响应体与 `Content-Length` | 上游 Transport 关闭自动压缩，`Accept-Encoding` 由客户端决定 | `keeps Content-Length for HEAD` |

## 4. 已知限制

- 307 / 308 指向上游自身主机但不在 `/v2/` 下的地址（例如某些仓库的下载接口）原样返回，客户端直连时没有凭证会失败。
  上述两类上游实测均不存在这种情况，出现时需要评估是否由代理跟随重定向。
- 会话 token 不加密，客户端可以读出上游的续传路径与 `_state` 参数。这些都不是凭证，接受该风险；审计日志不记录会话段。
