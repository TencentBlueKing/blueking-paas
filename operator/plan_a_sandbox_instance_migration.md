# 方案 A：AI Agent 应用运行时替换为 SandboxInstance —— 改造清单

> 目标：将 AI Agent 应用（`is_ai_agent_app=True`, `app_type=CLOUD_NATIVE`, `is_plugin_app=True`）
> 的运行时从「BkApp CR（经 app-operator 部署）」替换为「SandboxInstance CR（经 sandbox-controller 渲染 cube Pod）」，
> **保留标准部署链路骨架 + 插件应用全套对外能力 + HTTP 访问地址**。
>
> 方案 A 核心思想：**不另起炉灶，在标准云原生部署链路里按 `is_ai_agent_app` 分叉下发后端**，
> 复用部署历史（AppModelDeploy）、状态回填、地址解析（DomainGroupMapping）等既有资产。
>
> 代码引用相对 `apiserver/paasng/`。

---

## 〇、结论先行：影响面与复用性

调研澄清了三个关键事实，直接决定改造策略：

1. **运行态判据（云原生）**：`env_is_running` → `AppModelDeploy.objects.any_successful(env)`
   （`paas_wl/bk_app/cnative/specs/models/app_resource.py:276`），即「有一条 status=READY 的 AppModelDeploy」。
   → 只要 SandboxInstance 就绪后把 `AppModelDeploy.status` 置为 `READY`，运行态判断链路**原样复用**。

2. **地址解析来源**：云原生的 HTTP 访问入口由 `deploy_networking()`
   （`paas_wl/bk_app/cnative/specs/resource.py:132`）下发 `DomainGroupMapping` CR 产生 Ingress，
   **与 BkApp CR 是解耦的独立函数**。`save_addresses` 写地址 + `AddrResourceManager.build_mapping()` 下发映射。
   → SandboxInstance 场景可**直接复用 `deploy_networking(env)`**，只要 cube Pod 带标准 Service 选择器标签。

3. **下发锚点**：真正的下发函数是 `release_by_k8s_operator()`
   （`paasng/platform/engine/deploy/release/operator.py:99`），下发段在其内部（约 `:140-175`）。

**能力影响面结论**：
- 应用层能力（distributor 授权 / profile / 网关注册 / 环境变量注入）— **不受影响**，无需改动。
- 运行时层能力（部署历史 / 运行态判断 / 地址解析 / 日志采集）— 通过「写 AppModelDeploy + 复用 deploy_networking + 补 BKLogConfig」补偿。

---

## 一、改造锚点总览

| # | 改造点 | 文件位置 | 类型 |
|---|---|---|---|
| 1 | 部署 Step 分叉 | `paasng/platform/engine/deploy/release/operator.py:64` `BkAppReleaseMgr.start` | 分叉 |
| 2 | 下发后端分叉 | `operator.py:99` `release_by_k8s_operator` 内下发段 | 核心分叉 |
| 3 | SandboxInstance 下发适配 | 新建 `paasng/platform/engine/deploy/release/sandbox_operator.py`（新文件） | 新增 |
| 4 | 网络/地址解析补偿 | 复用 `paas_wl/bk_app/cnative/specs/resource.py:132` `deploy_networking` | 复用 |
| 5 | 状态轮询分叉 | `paasng/platform/engine/deploy/bg_wait/wait_bkapp.py:150` `WaitAppModelReady` | 分叉 |
| 6 | AppModelDeploy 状态回填 | `wait_bkapp.py:300` 附近 status→READY 写入 | 复用/适配 |
| 7 | 日志采集补偿 | `operator.py` `ensure_bk_log_if_need` 调用点 | 复用 |
| 8 | 集群分配（已就绪） | `paas_wl/infras/cluster/shim.py:92` | 无需改动 |

---

## 二、逐项改造详情

### 2.1 部署 Step 分叉（锚点 #1）

**位置**：`paasng/platform/engine/deploy/release/operator.py:64` `BkAppReleaseMgr.start()`

**现状**：无条件调用 `release_by_k8s_operator(...)`（`operator.py:80`）下发 BkApp。

**改造**：在 `start()` 内按 `env.application.is_ai_agent_app` 分叉：
```python
if self.module_environment.application.is_ai_agent_app:
    release_id = release_by_sandbox_instance(self.module_environment, revision, ...)
else:
    release_id = release_by_k8s_operator(self.module_environment, revision, ...)
```
- 轮询/step 标记逻辑（`operator.py:88-96`）保持不变，`release_id` 语义统一为 `AppModelDeploy.id`。

**注意**：`BkAppReleaseMgr` 的 docstring（`operator.py:59`）说明它调度 Deployment/Ingress by operator，改造后 AI Agent 分支改为由 sandbox-controller 调度，需更新注释。

---

### 2.2 下发后端分叉（锚点 #2，核心）

**位置**：`release_by_k8s_operator`（`operator.py:99`）内部下发段：
- `AppModelDeploy.objects.create(...)`（`operator.py:126`）——**保留**，部署历史记录。
- `get_bkapp_resource_for_deploy(...)`（`operator.py:142`）——AI Agent 分支替换为拼 SandboxInstanceSpec。
- `apply_bkapp_to_k8s(env, ...)`（`operator.py:170`，即 `cnative/specs/resource.py` 的 `deploy`）——替换为下发 SandboxInstance。
- `ensure_bk_log_if_need(env)` / `sync_service_monitor(env)`（`operator.py:173-175`）——见 2.7。

**改造**：新建 `release_by_sandbox_instance()`（放在锚点 #3 新文件），结构镜像 `release_by_k8s_operator`：

```python
def release_by_sandbox_instance(env, revision, operator, build, deployment) -> str:
    application = env.application
    # 1. 保留部署历史记录（复用现有模型）
    app_model_deploy = AppModelDeploy.objects.create(
        application_id=application.id, module_id=env.module.id,
        environment_name=env.environment, name=default_name,
        revision=revision, status=DeployStatus.PENDING.value,
        operator=operator, tenant_id=application.tenant_id,
    )
    # 2. 确保命名空间
    ensure_namespace(env)
    # 3. 拼装 SandboxInstanceSpec 并下发（复用已实现的资源层）
    spec = build_sandbox_spec_from_deploy(env, revision, build, deployment)
    SandboxInstanceManager(cluster_name).deploy(spec, wait_ready=False)  # 异步, 交给轮询
    # 4. 下发网络资源（复用云原生地址解析链路，见 2.4）
    deploy_networking(env)
    # 5. 日志采集（见 2.7）
    ensure_bk_log_if_need(env)
    return str(app_model_deploy.id)
```

**关键复用点**：
- `AppModelDeploy` 记录照写 → 满足 `any_successful` 运行态判据。
- `SandboxInstanceManager`：已实现于 `paas_wl/bk_app/sandbox_instance/resource.py`（本次改造前已完成的资源层）。
- 需新增 `build_sandbox_spec_from_deploy()`：从 `env` / `build.image` / `revision` / AI Agent 的进程配置拼 `SandboxInstanceSpec`。

**待决**：cube Pod 的 image 来源——AI Agent 走 buildpack/CUSTOM_IMAGE，`build.image` 即最终镜像，可直接作为 SandboxInstanceSpec.image。

---

### 2.3 SandboxInstance 下发适配层（锚点 #3，新文件）

**新建**：`paasng/platform/engine/deploy/release/sandbox_operator.py`

内容：
- `release_by_sandbox_instance(...)`（见 2.2）。
- `build_sandbox_spec_from_deploy(env, revision, build, deployment) -> SandboxInstanceSpec`：
  - `image = build.image`
  - `cpu_cores` / `memory`：从 AI Agent 的资源配置（BkApp spec 的 process resQuota 或 AI Agent 默认规格）解析。
  - `command` / `args`：从 revision 的 process command 解析。
  - `namespace = env.wl_app.namespace`（**对齐云原生命名空间**，而非 agent-sbx 命名空间——见「五、注意事项」）。
  - `rootfs` / `guest_mac`：按 AI Agent 隔离需求（`deploy_policy=ISOLATED`）决定。

---

### 2.4 网络 / 地址解析补偿（锚点 #4，复用）

**复用**：`deploy_networking(env)`（`paas_wl/bk_app/cnative/specs/resource.py:132`）

该函数做两件事，**均不依赖 BkApp CR**：
1. `save_addresses(env, protocol)` — 写入应用访问地址到 DB。
2. `AddrResourceManager(env).build_mapping()` + 下发 `DomainGroupMapping` CR（`resource.py:141`）— app-operator 据此建 Ingress。

**前提条件（必须满足，否则地址不通）**：
- SandboxInstance 渲染出的 cube Pod 必须带 **与云原生 Service 选择器一致的 label**，使 DomainGroupMapping → Service → Ingress 能选中 Pod。
- 需确认 sandbox-controller 是否会为 cube Pod 打上 `env.wl_app` 对应的标准标签；若不会，需在 SandboxInstanceSpec 的 pod template annotations/labels 中补齐。

**验证点**：`get_deployed_statuses`（`bk_plugins/models.py:273`）→ `ModuleEnvAvailableAddressHelper(env).addresses`（`market/utils.py:69`）应能返回非空地址。

---

### 2.5 状态轮询分叉（锚点 #5）

**位置**：`paasng/platform/engine/deploy/bg_wait/wait_bkapp.py:150` `WaitAppModelReady`

**现状**：`get_mres_from_cluster(...)`（`wait_bkapp.py:169`）读取 **BkApp CR** 的 status.conditions 判断就绪。

**改造**：AI Agent 分支需读取 **SandboxInstance CR** 的 `status.phase`（Running/Failed）而非 BkApp status。两种实现路径：
- **（推荐）** 新增 `WaitSandboxInstanceReady` poller（镜像 `WaitAppModelReady`），读取 SandboxInstance status，映射到 `DeployStatus`。
- 或在 `WaitAppModelReady` 内按 `is_ai_agent_app` 分叉读取源。

**就绪判据映射**：
| SandboxInstance phase | AppModelDeploy status |
|---|---|
| Running | READY |
| Failed | ERROR |
| Pending/Creating | PENDING（继续轮询） |

已实现的 `SandboxInstanceManager.wait_for_ready`（`sandbox_instance/resource.py`）逻辑可参考，但部署链路要的是**异步 poller**（`TaskPoller`），不能用同步阻塞轮询。

---

### 2.6 AppModelDeploy 状态回填（锚点 #6）

**位置**：`wait_bkapp.py:300` 附近，poller 完成后 `dp.save(update_fields=["status", ...])`（`wait_bkapp.py:307`）。

**改造**：`DeployStatusHandler`（`wait_bkapp.py:218`）或新 handler 在 SandboxInstance 就绪时，把 `AppModelDeploy.status` 置为 `DeployStatus.READY`。

**这是运行态判据成立的关键**——`env_is_running`（`app_resource.py:276`）依赖 `any_successful`（status=READY）。此步做对，则：
- `env_is_deployed` 返回 True（`exposer.py:34`）
- 插件 `get_deployed_statuses` 报告「已部署 + 地址」
- 使用方（AIDev/ITSM）能正常发现并调用。

---

### 2.7 日志采集补偿（锚点 #7）

**位置**：`operator.py:173` `ensure_bk_log_if_need(env)`；底层 `make_bk_log_controller`（`operator.py:34` import）。

**现状**：依赖 BkApp Pod 的 namespace/label 下发 `BKLogConfig`。

**改造**：SandboxInstance 分支同样调用 `ensure_bk_log_if_need(env)`，但需确认 cube Pod 的 namespace/label 与 BKLogConfig 的采集选择器匹配（与 2.4 的 label 要求同源）。若匹配则**直接复用**。

---

### 2.8 集群分配（锚点 #8，已就绪，无需改动）

**位置**：`paas_wl/infras/cluster/shim.py:92` `_get_cluster_usage`

已按 `is_ai_agent_app` + `deploy_policy` 返回 `AI_AGENT` / `AI_AGENT_ISOLATED` 集群 usage。
→ cube 运行时所需的隔离集群已由此分配，**改造无需触碰**。

---

## 三、改造顺序（建议）

1. **资源层**（已完成）：`paas_wl/bk_app/sandbox_instance/` 下发能力。
2. **适配层**：新建 `sandbox_operator.py`，实现 `release_by_sandbox_instance` + `build_sandbox_spec_from_deploy`（锚点 #3/#2）。
3. **网络复用验证**：确认 cube Pod label ↔ DomainGroupMapping/Service 选择器（锚点 #4），本地/测试集群跑通地址解析。
4. **状态轮询**：新建 `WaitSandboxInstanceReady` + 状态回填 AppModelDeploy=READY（锚点 #5/#6）。
5. **Step 分叉**：在 `BkAppReleaseMgr.start` 接入分叉（锚点 #1）。
6. **日志采集验证**：确认 BKLogConfig 采集到 cube Pod（锚点 #7）。
7. **端到端验证**：创建 AI Agent 应用 → 部署 → `get_deployed_statuses` 返回地址 → 网关调用通。

---

## 四、复用 vs 新增 清单

| 复用（不改） | 新增/改动 |
|---|---|
| `AppModelDeploy` 部署历史模型 | `release_by_sandbox_instance()` |
| `deploy_networking` / `DomainGroupMapping` 地址解析 | `build_sandbox_spec_from_deploy()` |
| `env_is_running` / `env_is_deployed` 判据 | `WaitSandboxInstanceReady` poller |
| `ensure_bk_log_if_need` 日志采集 | `BkAppReleaseMgr.start` 分叉逻辑 |
| 集群分配 `shim.py:92` | SandboxInstanceSpec 的 Pod label 补齐 |
| 插件全套能力（distributor/apigw/profile/env） | AppModelDeploy 状态回填改为 SandboxInstance 驱动 |
| `SandboxInstanceManager`（资源层） | — |

---

## 五、注意事项与待决问题

1. **命名空间对齐（关键）**：本次已实现的 SandboxInstance view 用的是 `bk-agent-sbx-{safe_app_id}`（Agent Sandbox 约定）。
   但方案 A 走标准部署链路，地址解析/日志采集/DomainGroupMapping 都基于 `env.wl_app.namespace`（云原生命名空间）。
   → **`build_sandbox_spec_from_deploy` 必须使用 `env.wl_app.namespace`，不能用 agent-sbx 命名空间**，否则网络与日志链路全断。

2. **cube Pod 标签**：地址解析（2.4）、日志采集（2.7）都要求 cube Pod 带云原生标准 label。
   需与 sandbox-controller 侧确认：SandboxInstance 渲染 Pod 时是否透传/继承 label，或需在 CR spec 显式声明。

3. **进程模型差异**：BkApp 支持多进程（web/worker...），SandboxInstance 是单 cube Pod。
   需确认 AI Agent 应用是否只需单进程；若需多进程，方案 A 需评估 SandboxInstance 是否支持或如何降级。

4. **Service/gRPC 暴露类型**：`sync_networking`（`resource.py:120`）按 BkApp 的 exposedType 决定 HTTP/gRPC。
   AI Agent 走 SandboxInstance 后，exposedType 信息来源需明确（从 revision/AppModelResource 读，还是固定 HTTP）。

5. **回滚与幂等**：`release_by_sandbox_instance` 失败时 `AppModelDeploy.status=ERROR` 的处理需对齐现有 try/except（`operator.py:176-185`）。

6. **本次已实现的独立接口去留**：`paasng/platform/sandbox_instance/`（独立 view/urls）与方案 A 是两种形态。
   若确定走方案 A（运行时替换），独立接口可保留作「运维手动管理沙箱实例」用途，或按需下线，避免双入口混淆。
