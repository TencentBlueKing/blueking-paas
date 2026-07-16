# AI Agent 应用接口扩展支持 sidecar

## 基本信息

| 字段 | 值 |
|------|-----|
| 需求 ID | 待创建 |
| 需求名称 | AI Agent 应用接口扩展支持 sidecar |
| 优先级 | High |
| 处理人 | porterlin |
| 父需求 | 1069995494136382733（AiAgent 应用支持多容器） |
| 依赖关系 | 强依赖子需求 1（CR 多容器声明能力）和子需求 2（镜像来源管理） |
| 原始需求文档 | docs/reqs/AI_Agent应用接口扩展支持sidecar.md |
| 预估工时 | 24 人时 |
| 价值规模 | 10（Reach=5, Impact=8, Confidence=75%, Effort=3人天） |

## 人力与工时

* 全量工作1位高级工程师完成工时预估：24 人时
* 全量工作1位中级工程师完成工时预估：32 人时

## 需求背景

### 业务背景

在 CR 层和镜像管理层就绪后，需要在 API 层打通整个链路，使 AI 平台团队能够通过 `create_ai_agent_app` 接口声明 sidecar 配置，并在部署时将配置传递到 SandboxInstance CR。

### 用户故事

作为 **内部 AI 平台团队**
我想要 **在调用 create_ai_agent_app 接口时传入 sidecar 容器配置（镜像、资源配额、端口）**
以便于 **创建包含多容器的 AI Agent 应用**

## 功能需求

### 核心功能点

| 功能编号 | 功能描述 | 优先级 | 备注 |
|---------|---------|--------|------|
| F-003-1 | 扩展 create_ai_agent_app 接口参数 | P0 | 新增 sidecar 配置字段 |
| F-003-2 | Sidecar 配置校验逻辑 | P0 | 镜像存在性、资源配额范围 |
| F-003-3 | Sidecar 配置持久化与部署传递 | P0 | 存入应用模型 + 传递给 CR |
| F-003-4 | 容器独立资源配额配置 | P1 | 每个容器独立 CPU/内存 |

### 详细功能描述

#### [F-003-1] 扩展 create_ai_agent_app 接口

- **输入**：原有接口参数 + 新增 `sidecars` 字段（数组）
- **处理逻辑**：
  1. 修改 `AIAgentAppCreateInputSLZ` 序列化器，新增 sidecars 字段（可选）
  2. 每个 sidecar 项包含：image（必填）、ports（选填）、resources（选填）、name（选填）
  3. 仅在 `DeployPolicy.ISOLATED` 模式下允许传入 sidecars
- **输出**：接口成功接收并处理 sidecar 参数
- **边界条件**：
  - sidecars 为空或不传时，行为与当前完全一致
  - 非 ISOLATED 模式传入 sidecars 返回 400 错误

#### [F-003-2] Sidecar 配置校验

- **输入**：sidecar 配置数组
- **处理逻辑**：
  1. 校验镜像地址格式合法性
  2. 校验镜像在镜像管理 DB 中存在（关联子需求 2）
  3. 校验资源配额在允许范围内
  4. 校验 sidecar 数量 ≤ 3
- **输出**：校验通过/失败（含具体错误信息）

#### [F-003-3] 配置持久化与部署传递

- **输入**：校验通过的 sidecar 配置
- **处理逻辑**：
  1. 将 sidecar 配置存入应用模型（新增字段或关联表）
  2. 部署时从应用模型读取 sidecar 配置
  3. 调用 SandboxInstanceManager（子需求 1 能力）构建含 sidecar 的 CR
- **输出**：完整部署链路打通

#### [F-003-4] 容器独立资源配额

- **输入**：每个 sidecar 容器的 resources 字段（cpu/memory 的 requests 和 limits）
- **处理逻辑**：
  1. 各容器独立声明资源限制
  2. 资源配额写入 CR spec 中对应容器的 resources 字段
- **输出**：Pod 中各容器按声明的资源运行

## 验收标准

### 功能验收

- [ ] **AC-001**：Given AI 平台团队调用 create_ai_agent_app 并指定 1 个 sidecar 容器 When deploy_policy 为 ISOLATED When 应用创建成功且 sidecar 配置已保存
- [ ] **AC-002**：Given 不传 sidecar 配置 When 调用 create_ai_agent_app Then 行为与当前单容器模式一致
- [ ] **AC-003**：Given deploy_policy 不是 ISOLATED 但传入了 sidecar 配置 When 调用接口 Then 返回 400 错误
- [ ] **AC-004**：Given 应用已创建含 sidecar 配置 When 触发部署 Then SandboxInstance CR 包含正确的 sidecar 声明
- [ ] **AC-005**：Given sidecar 镜像不在镜像管理 DB 中 When 校验 Then 返回镜像不存在错误

## 边界范围

### 本子需求包含

- AIAgentAppCreateInputSLZ 序列化器扩展
- sidecar 配置校验逻辑
- 应用模型扩展（sidecar 配置持久化）
- 部署流程中 sidecar 配置到 CR 的传递
- 容器独立资源配额
- 相关单元测试和集成测试

### 本子需求不包含

- SandboxInstance CR spec 定义（子需求 1）
- 镜像构建/注册能力（子需求 2）
- 前端 UI
