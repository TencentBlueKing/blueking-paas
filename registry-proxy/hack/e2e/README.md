# registry-proxy 端到端验证

在本机启动编译好的代理，用 kaniko 和 curl 走完整的 OCI 请求，验证构建、授权和凭证不外泄。
分为两类：

- **代理验收**：`10-local-smoke.sh`、`20-kaniko.sh`、`30-negative.sh`。请求经过代理。
- **上游行为探测**：`upload-session-probe.py`、`scope-probe.py`。用上游凭证直连仓库，不经过代理，
  用来确认「上传会话要不要由代理签名」「scope 要不要由代理计算」这两个设计前提。不能当作代理的验收。

单元测试、本地 `registry:2` 集成测试和性能基准在上一级：`make test`、`make integration`、`make bench`。

## 环境

需要 Docker、`curl`、`openssl`、`python3`（只用标准库）。kaniko 与 crane 以容器运行，镜像名在 `env.example.sh` 里。

`env.sh` 和 `.state/` 已被 gitignore。`env.sh` 放测试仓库地址和上游凭证路径；`.state/` 放编译产物、
代理生成的密钥、TLS 证书、合并后的上游凭证和审计日志。不要把这两个提交到仓库。

## 用法

### 本地冒烟（不需要真实仓库）

```bash
bash 00-build.sh
bash 10-local-smoke.sh
```

`10-local-smoke.sh` 自己起一个无认证的 `registry:2`，生成临时环境文件 `.state/env.local.sh`，
然后依次跑 `20-kaniko.sh` 和 `30-negative.sh`。结束时删掉这个 registry 容器。
只验证代理本身的协议和授权，不代表某个真实仓库的行为。

### 真实上游

```bash
cp env.example.sh env.sh   # 填写 CASES 与各 CASE_* 仓库地址，不要写入凭证本身
bash 00-build.sh
bash 20-kaniko.sh                      # 按 CASES 逐个构建
bash 30-negative.sh                    # 使用 env.sh 里的 NEGATIVE_CASE
bash 30-negative.sh BKREPO             # 或指定某一个用例
```

`env.sh` 的约定：

| 变量 | 作用 |
|------|------|
| `UPSTREAM_DOCKER_CONFIGS` | 逗号分隔的 docker config 路径。只交给代理进程和脚本里的直连校验，不挂进 kaniko 容器 |
| `CASES` | `20-kaniko.sh` 要跑的用例名，空格分隔。示例里是 `HARBOR BKREPO CROSS` |
| `CASE_<名>_BASE_IMAGE` | 带 tag 的基础镜像，必须含 `/bin/sh`。地址写真实仓库，脚本会改写成经代理的路径 |
| `CASE_<名>_PUSH_IMAGE` | 带 tag 的推送目标。`BASE_IMAGE` 或 `PUSH_IMAGE` 为空的用例会跳过 |
| `CASE_<名>_CACHE_REPO` | 不带 tag 的缓存仓库。填写后会构建两次，检查第二次命中缓存 |
| `NEGATIVE_CASE` | `30-negative.sh` 不带参数时使用的用例，取其 `BASE_IMAGE` 和 `PUSH_IMAGE` 构造请求 |
| `INSECURE_UPSTREAMS` | 明文 HTTP 的上游 host，逗号分隔。本地 registry 用，真实仓库留空 |
| `PROXY_HOST` / `PROXY_PORT` | 代理对外的主机名和端口。不要用 `127.0.0.1`：kaniko 会把回环地址当成明文 HTTP |

`CROSS` 用来覆盖跨上游 mount：base 和推送目标分属两个上游。
如果某个上游对其他仓库里已经存在的 blob 也返回存在，不要把它当作推送目标，否则 kaniko 不一定会发起 mount。

每个脚本结束时打印 `PASS` / `FAIL` 计数，有失败项时退出码非 0。
代理的标准输出是审计日志（`.state/audit.jsonl`），标准错误是运行日志（`.state/proxy.log`）。

### 上游行为探测

两个脚本都直连上游，参数里的仓库必须是推送账号有权限的测试仓库。输出只有状态码和结构，不含凭证。

```bash
python3 upload-session-probe.py <docker config> <上游主机> <仓库 A> <仓库 B>
python3 scope-probe.py <docker config> <上游主机> <仓库 A> <A 中已存在的 tag> <仓库 B>
```

`scope-probe.py` 的写操作只发起 `POST /blobs/uploads/`，不上传数据。

## 验收脚本覆盖的检查

### `20-kaniko.sh`：经代理构建

每个用例签发一个只授权本次推送仓库和 tag 的构建 token，kaniko 容器里只挂这个 token。

- kaniko 经代理拉取 base、推送产物，退出码为 0。
- Dockerfile 里的 `RUN` 探针读到了进程环境和 docker config，构建日志中上游凭证出现次数为 0。
- 经代理读回的 digest、直连上游读回的 digest，都与 kaniko 写出的 digest 一致。
- 填了缓存仓库时，第二次构建日志里出现 `Using caching version of cmd`。
- 该构建在审计中没有被拒绝的请求。kaniko 预检发出的 `DELETE` 返回 `delete_not_allowed`，不计入。

### `30-negative.sh`：协议与越权

越权请求在代理处被拒绝，不会转发到上游。只有「凭证不外泄」一节会访问上游。

| 分组 | 检查 |
|------|------|
| 认证与 `/v2/` 质询 | 无凭证 401 且质询为 `Basic realm="bkpaas-registry-proxy"`；有效 token 200；伪造签名、过期、其他集群的 token 均为 401 |
| 授权 | 未授权的 tag、未授权的仓库、删除 manifest、未配置的上游、没有 pull 授权时拉 base、`/v2/_catalog`、伪造的上传会话 |
| 凭证不外泄 | 经代理拉 base manifest 返回 200，响应里没有上游凭证、`WWW-Authenticate`、`Set-Cookie`；拿构建 token 直连上游换到的 token 不能发起上传 |
| 审计 | 审计日志里构建 token 和上游凭证的出现次数都是 0 |

## 文件

| 文件 | 内容 |
|------|------|
| `00-build.sh` | 把 `registry-proxy` 和 `hack/tokentool` 编译到 `.state/`。其他脚本要求这两个二进制已经存在 |
| `10-local-smoke.sh` | 起本地 `registry:2`，推入 `busybox:1.36`，生成 `.state/env.local.sh`，调用 20 和 30。不读取 `env.sh` |
| `20-kaniko.sh` | 按 `CASES` 跑构建。生成只含构建 token 的 docker config、带凭证探针的 Dockerfile，调用 kaniko，再用 crane 对比 digest |
| `30-negative.sh` | 用 `tokentool` 签发有效、无 pull、过期、其他 audience、伪造签名的 token，用 curl 打代理，并直连上游做凭证探针 |
| `lib.sh` | 被 20 和 30 source。加载 `env.sh`（可用 `E2E_ENV_FILE` 覆盖），提供断言（`expect` / `summary`）、代理启停、自签名证书与密钥生成、token 签发、仓库地址到代理路径的改写 |
| `helpers.py` | 只依赖标准库的子命令：合并 docker config、生成 token claims、在日志里统计凭证出现次数、审计汇总、拿构建 token 直连上游尝试上传。接触凭证的命令只打印计数或状态码 |
| `env.example.sh` | 环境变量模板。复制为 `env.sh` 后填写，`env.sh` 不进版本库 |
| `upload-session-probe.py` | 直连上游，比较「在本仓库续传」和「把上传会话拿到另一个仓库续传」，以及伪造上传 ID、篡改 `_state` 的结果 |
| `scope-probe.py` | 直连上游，打印未认证请求的质询 scope，再用不同 scope 换 token，看拉取和开始上传是否受 scope 限制 |
