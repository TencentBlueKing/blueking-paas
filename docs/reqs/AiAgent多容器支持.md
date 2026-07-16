# AiAgent 应用支持多容器

## 基本信息

| 字段 | 值 |
|------|-----|
| 需求 ID | 1069995494136382733 |
| 需求名称 | AiAgent 应用支持多容器 |
| 优先级 | High |
| 处理人 | porterlin |
| 父需求 | 无（根需求） |
| 创建时间 | 2026-07-22 11:28:57 |
| 原始需求文档 | docs/reqs/AiAgent多容器支持.md |

## 需求背景

### 业务背景

- **当前问题**：AI Agent 应用在 ISOLATED（安全合规隔离）模式下，通过 SandboxInstance CR 下发部署，目前仅支持单容器（web 进程），无法满足多容器协同的业务场景
- **目标**：支持在 SandboxInstance 中声明多个容器（1 个主容器 + N 个 sidecar 容器），实现主容器（适配层）与 AI Agent 容器（如 openclav）的分离部署
- **为什么现在做**：内部 AI 平台团队需要将适配层逻辑与实际 AI Agent 运行时解耦，便于独立迭代和运维
- **不做的影响**：AI Agent 应用只能将所有逻辑打包在单容器中，无法实现组件独立构建、独立升级

### 用户故事

作为 **内部 AI 平台团队**
我想要 **在创建 AI Agent 应用时能够声明多个容器（主容器 + sidecar）**
以便于 **将适配层和实际 AI Agent 运行时解耦，支持独立构建和独立升级**

作为 **内部 AI 平台团队**
我想要 **sidecar 容器的镜像可以通过平台构建或独立接口指定**
以便于 **灵活选择镜像来源，适配不同的 AI Agent 框架**

### 需求来源

- **需求渠道**：产品规划 / 技术架构演进
- **关联需求**：无
- **参考资料**：蓝鲸插件构建流程（可作为方案 A 的参考实现）

## 功能需求

### 核心功能点

| 功能编号 | 功能描述 | 优先级 | 涉及角色 | 备注 |
|---------|---------|--------|---------|------|
| F-001 | SandboxInstance CR 支持声明多容器 | P0 | AI 平台团队 | 主容器 + sidecar 容器 |
| F-002 | Sidecar 容器镜像来源管理 | P0 | AI 平台团队 | 方案待评审 |
| F-003 | 创建 AI Agent 应用时指定 sidecar 配置 | P0 | AI 平台团队 | 扩展 create_ai_agent_app 接口 |
| F-004 | Sidecar 容器资源配额独立配置 | P1 | AI 平台团队 | CPU/内存 limits |

### 详细功能描述

#### [F-001] SandboxInstance CR 支持声明多容器

- **输入**：应用部署请求（含多容器配置）
- **处理逻辑**：
  1. 平台构建 SandboxInstance CR 时，在 spec 中声明主容器和 sidecar 容器列表
  2. sandbox-controller 渲染 Pod 时包含所有声明的容器
  3. 所有容器共享同一 Pod 的 network namespace（通过 localhost 通信）
- **输出**：包含多容器的 Pod 正常运行
- **边界条件**：
  - 最多支持 1 个主容器 + 3 个 sidecar 容器
  - 主容器必须存在，sidecar 可选
- **异常处理**：
  - sidecar 容器启动失败 → Pod 整体标记为不健康，由 sandbox-controller 处理重启

#### [F-002] Sidecar 容器镜像来源管理（方案待评审）

**方案 A：复用蓝鲸插件构建流程**
- **输入**：用户提交源码
- **处理逻辑**：
  1. 复用蓝鲸插件的完整构建流程（源码 → 镜像）
  2. 构建产物作为 sidecar 镜像存储
- **优点**：后续蓝鲸插件有类似需求可复用
- **缺点**：实现复杂度较高

**方案 B：独立构建接口**
- **输入**：调用方通过独立构建接口提交构建请求
- **处理逻辑**：
  1. 提供独立的构建 API，调用方提交构建信息
  2. 构建完成后镜像信息存入后台 DB
  3. 创建 AI Agent 应用时从 DB 中选择已有镜像
- **优点**：实现简单，接口解耦
- **缺点**：不易复用到其他场景

> ⚠️ **决策待定**：两种方案需要评审后确定最终选择

#### [F-003] 创建 AI Agent 应用时指定 sidecar 配置

- **输入**：`create_ai_agent_app` 接口新增 sidecar 相关参数
- **处理逻辑**：
  1. 接口接收 sidecar 容器配置（镜像、资源配额、端口等）
  2. 校验配置合法性（镜像存在性、资源配额范围）
  3. 将 sidecar 配置存入应用模型
  4. 部署时将配置传递给 SandboxInstance CR
- **输出**：应用创建成功，包含 sidecar 配置
- **边界条件**：
  - sidecar 配置为空时等同于当前单容器行为（向后兼容）
  - 仅在 `DeployPolicy.ISOLATED` 模式下生效

#### [F-004] Sidecar 容器资源配额独立配置

- **输入**：每个 sidecar 容器的 CPU/内存 limits 和 requests
- **处理逻辑**：
  1. 每个容器独立声明资源限制
  2. 平台校验总资源不超过集群可分配额度
- **输出**：Pod 中各容器按声明的资源配额运行

## 非功能需求

### 性能需求

- **响应时间**：创建 AI Agent 应用接口响应时间 ≤ 3 秒
- **并发能力**：与当前 create_ai_agent_app 接口一致
- **数据容量**：单应用 sidecar 容器数量 ≤ 3

### 安全需求

- **权限控制**：仅内部 AI 平台团队有权通过 API 调用
- **数据保护**：镜像地址等敏感信息遵循现有安全规范
- **合规要求**：ISOLATED 模式的安全合规隔离特性不受影响

### 兼容性

- **接口兼容**：`create_ai_agent_app` 接口向后兼容，不传 sidecar 配置时行为不变
- **系统兼容**：需 sandbox-controller 支持多容器 CR 渲染

## 业务规则

### 业务逻辑规则

- **规则 R-001**：多容器仅在 `DeployPolicy.ISOLATED` 模式下支持
- **规则 R-002**：每个 Pod 有且仅有 1 个主容器，sidecar 容器数量为 0~3
- **规则 R-003**：同 Pod 内所有容器通过 localhost 通信
- **规则 R-004**：sidecar 容器的生命周期由 sandbox-controller 统一管理

### 数据校验规则

- **必填字段**：主容器镜像必填；sidecar 若声明则镜像必填
- **格式要求**：镜像地址需符合 OCI 镜像格式规范
- **取值范围**：资源配额需在集群允许的范围内

### 权限规则

- 仅 AI 平台团队服务账号可调用创建接口

## 外部依赖与集成

### 外部系统集成

| 系统名称 | 交互方式 | 接口说明 | 认证方式 | 文档链接 |
|---------|---------|---------|---------|---------|
| sandbox-controller | K8s CR | 渲染 SandboxInstance → Pod | ServiceAccount | 待确认 |
| 镜像仓库 | HTTP | 镜像拉取/推送 | imagePullSecrets | 待确认 |

### 数据模型

- SandboxInstance CR 需要扩展 spec 字段以支持 sidecar 容器列表声明
- 平台侧需要存储 sidecar 镜像信息（方案 B）或构建记录（方案 A）

## 验收标准

### 功能验收

- [ ] **AC-001**：Given AI 平台团队通过 API 创建 ISOLATED 模式的 AI Agent 应用并指定 1 个 sidecar 容器 When 应用部署完成 Then Pod 中包含 2 个容器（主容器 + sidecar），且均正常运行
- [ ] **AC-002**：Given AI 平台团队创建 AI Agent 应用但不指定 sidecar 配置 When 应用部署完成 Then 行为与当前单容器模式一致（向后兼容）
- [ ] **AC-003**：Given sidecar 容器镜像已通过构建/注册流程准备好 When 创建 AI Agent 应用并指定该镜像 Then sidecar 容器使用指定镜像启动成功
- [ ] **AC-004**：Given 主容器和 sidecar 容器均已启动 When 主容器通过 localhost:<port> 访问 sidecar 容器 Then 网络通信成功

### 性能验收

- [ ] **AC-P01**：创建 AI Agent 应用接口（含 sidecar 配置）响应时间 ≤ 3 秒

### 安全验收

- [ ] **AC-S01**：ISOLATED 模式下多容器 Pod 的网络隔离策略与单容器时一致

## 边界范围

### 本期包含

- SandboxInstance CR 多容器声明能力
- create_ai_agent_app 接口扩展（支持 sidecar 参数）
- Sidecar 容器镜像来源管理（方案选型 + 实现）
- 容器独立资源配额配置

### 本期不包含

- 非 ISOLATED 模式（普通模式）的多容器支持
- 前端 UI 操作界面
- sidecar 容器的日志采集和监控告警（沿用现有 Pod 级别监控）
- sidecar 容器的自动扩缩容

## 约束条件

- **技术限制**：依赖 sandbox-controller 对多容器 CR 的支持
- **适用场景**：仅限 `DeployPolicy.ISOLATED` + `is_ai_agent_app=True`

## 未解决问题

| 问题 ID | 问题描述 | 负责人 | 截止日期 | 状态 |
|--------|---------|--------|---------|------|
| Q-001 | Sidecar 镜像来源方案选择（方案 A vs 方案 B） | porterlin | 待定 | 待评审 |
| Q-002 | sandbox-controller 多容器 CR 字段设计需协调确认 | 待定 | 待定 | 待确认 |
| Q-003 | sidecar 容器健康检查策略（是否需要独立 probe） | 待定 | 待定 | 待确认 |

---

## 原需求描述

> 背景：
>
> 用户在使用 AI Agent 时（创建入口 apiserver/paasng/paasng/platform/applications/views/creation.py#L198 create_ai_agent_app）且指定 isolated 时， 需要通过 sandboxinstace cr 下发。 且在此基础上需要支持多个 sidecar 容器， 目前 设计为 一个主容器用于搭载主要业务逻辑（适配层）， 一个容器用于搭载实际的 AI Agent （如 openclaw）。
>
> 这里多 sidecar 的构建有两种思路：
> 1. 完全和之前蓝鲸插件的设计保持一致， 有完整的构建流程。 这种实现方式如果后续蓝鲸插件有需要也可以复用
> 2. 单独提供一个构建接口， 调用方通过构建接口构建后对应的镜像等信息被存入后台db， 构建 AI Agent 应用时可以选择其中的镜像作为 sidecar 容器的镜像。预计这种方式实现上更简单， 但是后续不太好复用到其他场景。

## 澄清记录

### 第 1 轮澄清

**提问时间**：2026-07-22

**Agent 提问**：
1. [What-01] 两种实现思路是否已确定选择哪种？
2. [What-02] sidecar 容器的镜像来源是什么？
3. [Who-03] 目标用户是谁？
4. [What-04] 多容器之间的网络通信方式？
5. [What-05] sidecar 容器数量上限？
6. [What-06] 是否需要独立资源配额？
7. [How-07] 健康检查和生命周期管理？
8. [When-08] 是否仅限 ISOLATED 模式？

**用户回复**：
1. 尚未决定，需要在需求文档中列为待评审项
2. 未确定，基于方案 A 可能是用户提交源码平台构建，基于方案 B 是用户调用单独接口创建镜像后在 create_ai_agent_app 接口中指定
3. 内部 AI 平台团队（通过 API 对接）
4. 同 Pod 内通过 localhost 通信
5. （使用默认假设：最多 1 主容器 + 3 sidecar）
6. （使用默认假设：每个容器独立配置资源限制）
7. （使用默认假设：由 sandbox-controller 统一管理）
8. （使用默认假设：仅限 ISOLATED 模式）
