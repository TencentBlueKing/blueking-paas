# 架构约束（Architectural Constraints）

> 目标：让 Agent "做正确的事"——通过刚性约束确保代码结构的一致性和可维护性。
> 本项目的分层依赖由 `apiserver/paasng/.importlinter`（import-linter 契约）**强制**，Go 侧由 `golangci-lint` 强制。

## 1. 分层架构模型

### 1.1 顶层模块边界（控制面 / 数据面）

```
webfe (Vue)  bkpaas-cli (Go)            ← 通过 REST API 接入
      │              │
      ▼              ▼
   apiserver (Python/Django 控制面)
      │  paasng（业务领域） + paas_wl（K8s 工作负载桥接）
      │
      │  下发声明式 CRD（BkApp / DomainGroupMapping ...）
      ▼
   operator (Go/kubebuilder 数据面)      ← watch CRD 并调和为 K8s 资源
      │
      ├── 增强服务 svc-*（统一 paas-service 协议，HTTP/REST，可插拔）
      └── sandbox daemon（HTTP，供 dev_sandbox 调用）
```

- **apiserver ↔ operator 只能通过 CRD / K8s API 间接交互**，禁止直接 RPC 调用
- **apiserver ↔ svc-\* 只能通过 `paasng/accessories/servicehub` 编排**，遵循 `paas-service` 协议
- **前端 / CLI ↔ apiserver 只能通过 REST API**，前后端完全分离

### 1.2 apiserver `paasng` 主分层（layers-main）

依赖只能**向下**流动，高层可依赖低层，低层不得引用高层：

```
paasng.plat_admin     （最高层：平台管理系统）
  ↓
paasng.bk_plugins     （蓝鲸插件、插件开发中心）
  ↓
paasng.platform       （核心业务：applications/modules/engine/bkapp_model/sourcectl...）
  ↓
paasng.accessories    （增强能力：servicehub/log/cloudapi/ci/dev_sandbox...）
  ↓
paasng.infras         （外部系统对接：iam/oauth2/bk_apigw/bkmonitorv3/bk_log/bcs...）
  ↓
paasng.core           （最底层核心：tenant 多租户、region 版本区域）
```

- **独立模块（independence 契约）**：`paasng.misc.metrics`、`paasng.misc.tracing`、`paasng.misc.changelog`、`paasng.misc.plat_config` 相互之间**不得**互相依赖
- **已知临时豁免**（`.importlinter` 的 `ignore_imports`）：`platform.applications/modules/engine/sourcectl/templates` 等尚未完全解耦，属于待偿还的技术债，**新代码不得扩大这些豁免范围**

### 1.3 `paasng.platform.engine` 子分层（layers-engine）

```
deploy | streaming  →  workflow | processes  →  phases_steps  →  utils  →  configurations  →  models
```

### 1.4 `paas_wl` 工作负载分层（layers-paas-wl）

```
paas_wl.apis  →  paas_wl.bk_app  →  paas_wl.workloads  →  paas_wl.core  →  paas_wl.infras  →  paas_wl.utils
```

- `paas_wl.infras.resources` 子分层（layers-paas-wl-resources）：`kube_res → generation → utils → base`
- `paas_wl` 是 apiserver 与 Kubernetes 之间的**桥接层**：`infras/resources/base/crd.py` 定义 CRD 客户端，`generation/v1.py`、`v2.py` 生成 CRD manifest 并下发

### 1.5 operator（Go）职责边界

- CRD 定义位于 `operator/api/`（`BkApp` v1alpha1/**v1alpha2**、`DomainGroupMapping`、`ProjectConfig`），含 conversion/defaulting/validation webhook
- Controller 位于 `operator/controllers/`，核心调和逻辑位于 `operator/pkg/controllers/`
- **CRD schema 是 apiserver 与 operator 的共享契约**，`operator/api/v1alpha2/bkapp_types.go` 变更必须同步 apiserver `paas_wl` 侧的生成逻辑

## 2. 强制约束规则（Linter）

### 2.1 规则清单

| 规则编号 | 名称 | 工具 | 描述 | 修复指引 |
|---------|------|------|------|---------|
| ARCH-001 | 主分层单向依赖 | import-linter（layers-main） | 低层模块不得引用高层模块 | 将被依赖的能力下沉到更低层，或在高层编排 |
| ARCH-002 | 模块独立性 | import-linter（independent-apps） | `misc.metrics/tracing/changelog/plat_config` 不得互相依赖 | 提取共享逻辑到 `utils` 或 `core` |
| ARCH-003 | engine 子分层 | import-linter（layers-engine） | engine 内部依赖须遵循 deploy→...→models | 调整调用方向或下沉公共逻辑 |
| ARCH-004 | paas_wl 分层 | import-linter（layers-paas-wl） | 违反 apis→...→utils 顺序 | 通过下层抽象访问，避免反向引用 |
| ARCH-005 | 不得扩大豁免 | 人工 + Review | 新代码不得新增/扩大 `.importlinter` 的 ignore_imports | 遵循分层重构，而非添加豁免 |
| LINT-PY | Python 规范 | ruff（line-length 119, py311）+ mypy | 见 `pyproject.toml` 规则集 | 按 ruff 提示修复，`ruff check --fix` |
| LINT-GO | Go 规范 | golangci-lint（含 revive 导出注释） | 见 `operator/.golangci.yaml` | `make fmt && make lint` |
| LINT-FE | 前端规范 | ESLint（@blueking/eslint-config-bk） | 见 `webfe` `.eslintrc.js` | `npm run lint` |

### 2.2 错误信息格式

Linter 错误信息应直接包含修复指引，让 Agent 能自主修复：

```
[ARCH-001] 违反主分层依赖：paasng.core.tenant 引用了 paasng.infras.bk_user
修复方式：core 为最底层，不得依赖 infras；应在 infras 或更高层编排该调用，
或将被依赖的最小能力下沉到 core。
参考文档：docs/harness/architectural-constraints.md#12-apiserver-paasng-主分层
```

## 3. Parse, Don't Validate

在数据进入系统的边界处，将原始数据**解析**为强类型模型，后续代码只操作解析后的类型。

| 边界 | 输入类型 | 解析目标 | 处理位置 |
|------|---------|---------|---------|
| REST API 请求 | JSON/Form | DRF Serializer 校验后的数据 | `views.py` / `serializers.py`（API 层保持薄） |
| CRD / K8s 资源 | YAML/JSON | 强类型 CRD 模型 | operator `api/*/types.go`、apiserver `paas_wl` crd 客户端 |
| 增强服务响应 | JSON | 领域模型 | `accessories/servicehub` adapter |
| 配置文件 | 环境变量/settings | Django settings 类型 | 启动阶段 `paasng/settings/` |

> 约定：**业务逻辑放 domain/service 层，API 层（views/serializers）保持薄**（keep API layer wiring thin）。

## 4. 架构决策记录（ADR）

- 存储位置：`docs/adr/`（如需引入）
- 命名格式：`NNNN-标题.md`
- 现有设计说明散见于 `apiserver/design_notes/`、`operator/README.md`，做架构决策前应先检索，确保与历史决策一致
- ADR 模板：状态（已接受/已废弃/已替代）→ 背景 → 决策 → 后果

## 检查清单

- [ ] 分层架构模型已定义，依赖方向明确（import-linter 契约）
- [ ] 至少 3 条自定义 Linter 规则已制定并接入 pre-commit
- [ ] 错误信息包含修复指引和参考文档链接
- [ ] 数据边界处的 Parse 策略已明确（DRF Serializer / CRD 类型）
- [ ] 新代码未扩大 `.importlinter` 的 ignore_imports 豁免
