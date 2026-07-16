# Code Review: SandboxInstance CR 发布链路

审查对象 commit: `29206056` — `feat(sandbox): support release sandboxinstance cr for ai agent app`

整体设计清晰、解耦良好：`SandboxInstanceManager` 只复用底层通用的 CR 下发能力，与 BkApp 数据模型解耦；复用 `AppModelDeploy` / `save_addresses` / `AppDefaultIngresses` 也合理。以下问题按严重程度排序。

---

## 🔴 Bug 1：`_parse_cpu_cores` 对小数核数「向上取整」实现错误

文件：`apiserver/paasng/paasng/platform/engine/deploy/release/sandbox_operator.py`（`_parse_cpu_cores`）

```python
cores = -(-int(float(cpu)) // 1) if "." in cpu else int(cpu)
```

`int(float("2.5"))` 先把小数**截断**成 `2`，再 `-(-2 // 1)` = 2。所以 `"2.5"` 得到 `2` 而非期望的向上取整 `3`。注释宣称「向上取整」，但对非整数核数是错的。

验证结果：

| 输入 | 期望(向上取整) | 实际 |
|------|------|------|
| `2.5` | 3 | 2 ❌ |
| `1.0` | 1 | 1 ✅ |
| `4000m` | 4 | 4 ✅ |
| `1500m` | 2 | 2 ✅ |

`m` 分支的 `-(-millicores // 1000)` 是对的，问题只在小数分支。

建议修复：

```python
import math
cores = math.ceil(float(cpu))  # "2.5" -> 3
```

---

## 🔴 Bug 2：Service targetPort 与 cube Pod 监听端口无契约保证

文件：`apiserver/paasng/paasng/platform/engine/deploy/release/sandbox_operator.py`（`deploy_sandbox_networking`）
关联：`apiserver/paasng/paas_wl/bk_app/sandbox_instance/entities.py`（`_build_main_container`）

`deploy_sandbox_networking` 用 `build_process_service`，其 `target_port=settings.CONTAINER_PORT`（BkApp 约定的容器端口）。但 `SandboxInstanceSpec._build_main_container` **完全没有声明容器端口**，也没有向 cube 传递 `CONTAINER_PORT` 环境变量。

结果：Service 会把流量转发到 `CONTAINER_PORT`，但 cube Pod 里应用实际监听什么端口不受控。若 AI Agent 镜像不恰好监听 `settings.CONTAINER_PORT`，Ingress → Service → Pod 链路会连不通（502）。

建议：在 spec 里显式声明端口，并/或把 `PORT`/`CONTAINER_PORT` 注入到 cube 容器 env，与普通应用对齐。

---

## 🟠 设计缺陷 3：超时（15 分钟）后 `AppModelDeploy.status` 悬挂在 PENDING

文件：`apiserver/paasng/paasng/platform/engine/deploy/bg_wait/wait_sandbox.py`（`WaitSandboxInstanceReady.get_status`）

`get_status` 只在 phase 为 `RUNNING`/`FAILED` 时返回 `done`，其余一律 `doing`。当沙箱长时间卡在 `Creating` 直到 `overall_timeout_seconds`(15min) 触发时，超时不会走 `DeployStatusHandler` 的成功/错误分支去把 status 置为 ERROR —— `AppModelDeploy.status` 会一直留在 `PENDING`。

后果：`env_is_running` 基于 `filter(status=READY)`，虽不会误判为运行中，但这条部署既不成功也不失败，前端部署历史长期挂起。对比 BkApp 链路（`WaitAppModelReady`）对中间态 `PROGRESSING` 也会 `update_status`。

建议：中间态也 `update_status` 刷新，并确认超时回调能落到 ERROR。

---

## 🟠 设计缺陷 4：`create_or_update(update_method="replace")` 对 CR 有丢状态风险

文件：`apiserver/paasng/paas_wl/bk_app/sandbox_instance/resource.py`（`SandboxInstanceManager.deploy`）

`deploy` 用 `replace` + `auto_add_version=True`。`replace` 是整体覆盖：用后端拼装的 manifest 覆盖整个对象，而拼装的 manifest **不含 sandbox-controller 可能回写的 spec/annotation 字段**（如 finalizer、`restartedAt` 之外的注解）。

重复下发时，`replace` 可能覆盖掉 controller 已写入的字段。而且 `restart()` 用 `patch` 加的 `restartedAt` 注解，若之后又走一次 `deploy()` 的 `replace`，会被抹掉。CR 通常推荐用 `patch` / server-side apply 而非整体 replace。

建议：`deploy` 评估改用 `patch` / apply 语义。

---

## 🟡 优化项 5：`_find_process` 回退到「首个进程」与固定 `web` 语义冲突

文件：`apiserver/paasng/paasng/platform/engine/deploy/release/sandbox_operator.py`（`_find_process` / `build_sandbox_spec_from_deploy`）

注释与常量都强调「AI Agent 单进程，固定 web」，但 `_find_process` 找不到 `web` 时 `return processes[0]`。既然是固定单进程模型，找不到 `web` 更应显式报错（`SandboxInstanceDeployError` 或 error_code），静默回退到任意首进程会掩盖配置错误。

---

## 🟡 优化项 6：`error_codes.py` 新增的三个 error code 未被使用

文件：`apiserver/paasng/paasng/utils/error_codes.py`

`SANDBOX_INSTANCE_DEPLOY_FAILED` / `SANDBOX_INSTANCE_READY_TIMEOUT` / `SANDBOX_INSTANCE_NOT_FOUND` 定义了但全链路无任何地方 `raise`。`sandbox_operator` 里异常直接向上抛并把 `AppModelDeploy.status` 置 ERROR，这三个 code 目前是死代码。

建议：在对应异常边界用上，或先不加。

---

## 🟡 优化项 7：多处未使用代码（为后续 PR 预留？）

文件：`resource.py` / `entities.py` / `constants.py`

- `RootfsConfig`、`SandboxInstanceManager.restart` / `set_desired_state` / `delete`
- `SandboxInstanceSpec.guest_mac`
- `SandboxInstancePhase.STOPPING` / `TERMINATING`

本 commit 内均无调用方。若为后续 PR 预留可接受，但当前属未被测试覆盖的未使用代码，建议 commit 说明注明或拆分。

---

## 🟢 其它小点

- `deploy_sandbox_networking` 里 Service 用 `get` 判存在再 `create`，非原子，存在 TOCTOU（并发部署可能 create 冲突）。发布链路串行，风险低。
- 缺少针对新链路的单元测试。`_parse_cpu_cores`、`build_manifest`、`BkAppReleaseMgr` 分叉逻辑都值得补测试 —— 一个 `_parse_cpu_cores` 的参数化测试即可暴露 Bug 1。
- `command`/`args` 兜底 (`if proc else []`) 正确，无空指针风险。

---

## 备注：IDE 中的 `eni_ip` 代码

IDE 上下文显示 `entities.py:158-163` 存在 `eni_ip` 分支（申请 `tke.cloud.tencent.com/eni-ip` 资源），但当前 git 工作区该文件为 164 行且不含此逻辑，本审查以已提交的 commit `29206056` 内容为准。若后续引入 `eni_ip`，需注意：`eni-ip` 属于容器 `resources.limits/requests`，而 SandboxInstance 走 cube runtime（MicroVM），需确认该 TKE 扩展资源在 cube Pod 渲染链路上是否被 sandbox-controller 正确透传，否则申请无效。

---

## 优先级建议

优先处理：**Bug 1**（CPU 解析，易修）、**Bug 2**（端口契约，影响连通性）、**缺陷 3**（超时状态悬挂，影响体验）。
