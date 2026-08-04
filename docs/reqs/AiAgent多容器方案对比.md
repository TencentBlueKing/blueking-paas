# SandboxInstance CR 下发架构方案对比

## 核心问题

**SandboxInstance CR 由谁负责下发和管理：apiserver 直接下发，还是通过 BkApp + app-operator 调和下发？**

这是一个架构层面的选择，决定了隔离型应用在整个平台中的管控模式。

---

## 当前架构现状

```
标准模式:   apiserver → BkApp CR → app-operator → Deployment/Service/Ingress → Pod
隔离模式:   apiserver → SandboxInstance CR → sandbox-controller → Pod
                     ↘ Service/Ingress（apiserver 自建，绕过 operator）
```

**现状问题**：隔离模式是一条"旁路"，平台侧（sandbox_operator.py）承担了本应由 operator 负责的多项职责：
- 构建完整 CR spec（环境变量、资源配额、调度配置、DNS 等）
- 自建 Service / Ingress（绕过 app-operator 的网络管理）
- 状态轮询和同步（WaitSandboxInstanceReady）
- 生命周期管理（重启、删除）

---

## 方案对比

### 方案 A：apiserver 直接下发 SandboxInstance CR（当前方案）

```
apiserver  ──→  SandboxInstance CR  ──→  sandbox-controller  ──→  Pod
    │
    └──→  Service / Ingress（平台自建）
```

### 方案 B：apiserver 下发 BkApp，app-operator 调和出 SandboxInstance CR

```
apiserver  ──→  BkApp CR  ──→  app-operator  ──→  SandboxInstance CR  ──→  sandbox-controller  ──→  Pod
                                     │
                                     └──→  Service / Ingress（operator 管理）
```

---

## 维度对比

| 维度 | 方案 A：apiserver 直接下发 | 方案 B：BkApp + app-operator 调和 |
|------|--------------------------|----------------------------------|
| **职责边界** | apiserver 既是控制面又是数据面（构建 CR + 下发 + 网络资源管理） | apiserver 只负责声明（BkApp），operator 负责集群侧资源调和 |
| **关注点分离** | 差。平台代码耦合了集群资源管理细节（Service/Ingress 创建、CR spec 组装） | 好。平台只关心"要什么"，operator 关心"怎么做" |
| **一致性** | 隔离模式与标准模式是两套独立逻辑，维护成本翻倍 | 统一为 BkApp → operator 模式，隔离只是 operator 内部的一个分支 |
| **可观测性** | 状态散落在 SandboxInstance CR + 平台 DB，无统一视图 | BkApp.status 作为统一状态汇聚点，所有信息一处可查 |
| **自愈能力** | 无。Service/Ingress 被误删后平台不感知，需要重新部署 | operator 持续 reconcile，自动修复漂移状态 |
| **配置变更** | 每次变更需 apiserver 主动重新下发 CR + 更新网络资源 | 修改 BkApp 声明即可，operator 检测变更自动滚动 |
| **网络管理** | 平台自建 Service/Ingress，与标准模式的 DomainGroupMapping 体系割裂 | operator 统一管理，与标准模式共享网络策略 |
| **故障域** | apiserver 挂了 → 新部署停止，但已运行应用不受影响 | operator 挂了 → 新变更无法调和，但已运行应用不受影响 |
| **扩展成本** | 每增加一个新能力（如多容器、配额变更、灰度发布）都需要改 apiserver | 新能力优先在 operator 侧实现，apiserver 只需扩展 BkApp 声明 |
| **开发语言** | Python（apiserver 团队熟悉） | Go（需要 operator 团队参与） |
| **发布节奏** | 仅平台发布，快 | 需协调 operator 升级，依赖集群侧发布窗口 |
| **调试链路** | 短：apiserver → CR → Pod | 长：apiserver → BkApp → operator → CR → Pod |

---

## 关键判断点

### 方案 A 更适合的场景

- 隔离模式是**少量、低频**使用的边缘场景
- 团队结构上 operator 开发资源紧张
- 隔离模式的需求**不会持续增长**（不会有更多新能力加入）
- 集群 operator 升级审批流程重、发布周期长

### 方案 B 更适合的场景

- 隔离模式是**核心能力**，预期大量 AI Agent 应用使用
- 后续需要持续为隔离应用增加新能力（多容器、灰度、自动扩缩容等）
- 需要自愈和持续调和能力（配置漂移自动修复）
- 需要与标准模式共享网络管理、监控、日志等基础设施逻辑
- 希望 apiserver 保持"薄"控制面，不膨胀为集群资源管理器

---

## 方案 B 所需变更项

### apiserver 侧（Python）

| 序号 | 变更项 | 涉及文件 | 说明 |
|------|--------|---------|------|
| 1 | ISOLATED 模式部署改为下发 BkApp | `platform/engine/deploy/release/operator.py` | 去掉 L88 的 ISOLATED 分支，统一走 `release_by_k8s_operator()` |
| 2 | BkApp spec 扩展隔离标识 | `paas_wl/bk_app/cnative/specs/crd/bk_app.py` | 新增 `deployPolicy: isolated` 字段，告知 operator 产出 SandboxInstance 而非 Deployment |
| 3 | 移除平台自建网络资源逻辑 | `sandbox_operator.py` 中 `deploy_sandbox_networking()` | 不再由平台直接创建 Service/Ingress |
| 4 | 状态同步统一 | 复用标准模式的 BkApp 状态轮询逻辑 | 不再单独实现 `WaitSandboxInstanceReady` |
| 5 | sandbox_operator.py 可废弃 | 整个文件逻辑迁移到 operator | 平台侧代码量减少 |

### app-operator 侧（Go）

| 序号 | 变更项 | 说明 |
|------|--------|------|
| 1 | 识别 BkApp.spec.deployPolicy | 当值为 `isolated` 时进入 SandboxInstance 调和分支 |
| 2 | 新增 SandboxInstance reconciler | 从 BkApp spec 构建 SandboxInstance CR（环境变量、资源配额、镜像等） |
| 3 | 网络资源调和 | 为隔离应用创建 Service/Ingress（复用现有网络管理逻辑或新增适配） |
| 4 | 状态回写 | SandboxInstance.status → BkApp.status.conditions |
| 5 | RBAC 扩展 | ServiceAccount 增加 SandboxInstance CRUD 权限 |
| 6 | Owner Reference | SandboxInstance 设置 ownerRef 指向 BkApp，确保级联删除 |

### 基础设施

| 序号 | 变更项 |
|------|--------|
| 1 | BkApp CRD 升级（新增 deployPolicy 字段） |
| 2 | app-operator 镜像升级部署 |
| 3 | ClusterRole 更新（SandboxInstance 权限） |

---

## 决策建议

**如果隔离模式是平台的长期核心能力（AI Agent 是未来重要方向）**，推荐方案 B。理由：

1. 当前 sandbox_operator.py 本质上是在 apiserver 里"手写了一个简化版 operator"，随着能力增加（多容器、配置热更新、灰度等）这部分代码会持续膨胀
2. apiserver 不应该直接管理集群侧资源的生命周期，这违反了控制面/数据面分离原则
3. 方案 B 让隔离模式自然获得 operator 的自愈、持续调和、级联删除等能力，不需要逐个在平台侧重新实现

**如果隔离模式只是临时/边缘能力**，保持方案 A 即可，避免过度设计。

---

## 折中路径

可以分两步走：
1. **短期**：在方案 A 基础上完成多容器需求（不阻塞交付）
2. **中期**：将 sandbox_operator.py 的逻辑整体迁移到 app-operator，apiserver 改为下发 BkApp（架构归一）

这样第一步的代码后续会被替换，但交付压力可控，且第二步有明确的重构目标。
