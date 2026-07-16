# SandboxInstance CR 多容器声明能力

## 基本信息

| 字段 | 值 |
|------|-----|
| 需求 ID | 待创建 |
| 需求名称 | SandboxInstance CR 多容器声明能力 |
| 优先级 | High |
| 处理人 | porterlin |
| 父需求 | 1069995494136382733（AiAgent 应用支持多容器） |
| 依赖关系 | 无（基座能力，其他子需求依赖本需求） |
| 原始需求文档 | docs/reqs/SandboxInstance_CR多容器声明能力.md |
| 预估工时 | 24 人时 |
| 价值规模 | 10（Reach=5, Impact=8, Confidence=75%, Effort=3人天） |

## 人力与工时

* 全量工作1位高级工程师完成工时预估：24 人时
* 全量工作1位中级工程师完成工时预估：32 人时

## 需求背景

### 业务背景

SandboxInstance CR 是 ISOLATED 模式 AI Agent 应用部署的载体。当前 CR spec 仅支持声明单容器，需要扩展支持多容器（主容器 + sidecar 列表）声明能力，为上层 API 和镜像管理提供基座。

### 用户故事

作为 **内部 AI 平台团队**
我想要 **SandboxInstance CR 能够声明多个容器（主容器 + sidecar 列表）**
以便于 **部署的 Pod 中运行多个独立容器实现适配层与 AI Agent 运行时解耦**

## 功能需求

### 核心功能点

| 功能编号 | 功能描述 | 优先级 | 备注 |
|---------|---------|--------|------|
| F-001-1 | SandboxInstance CR spec 扩展设计 | P0 | 新增 sidecars 字段定义 |
| F-001-2 | SandboxInstanceManager 构建逻辑扩展 | P0 | 支持构建含 sidecar 的 CR |

### 详细功能描述

#### [F-001-1] CR spec 扩展设计

- **输入**：sidecar 容器配置列表（镜像、端口、资源配额、名称）
- **处理逻辑**：
  1. 在 SandboxInstance CR spec 中新增 `sidecars` 字段（数组）
  2. 每个 sidecar 项包含：name、image、ports、resources
  3. 与 sandbox-controller 协调字段定义
- **输出**：CR spec 支持多容器声明
- **边界条件**：
  - sidecars 为空数组时等同于当前单容器行为
  - 最多声明 3 个 sidecar 容器

#### [F-001-2] SandboxInstanceManager 构建逻辑扩展

- **输入**：部署请求（含 sidecar 配置）
- **处理逻辑**：
  1. 修改 `SandboxInstanceManager` 的 CR 构建方法
  2. 将 sidecar 配置列表序列化到 CR spec.sidecars 字段
  3. 保持原有单容器逻辑不变（向后兼容）
- **输出**：生成包含多容器声明的 SandboxInstance CR
- **关键文件**：
  - `paas_wl/bk_app/sandbox_instance/resource.py`
  - `platform/engine/deploy/release/sandbox_operator.py`

## 验收标准

### 功能验收

- [ ] **AC-001**：Given 部署请求包含 1 个 sidecar 配置 When SandboxInstanceManager 构建 CR Then CR spec 中包含正确的 sidecars 字段
- [ ] **AC-002**：Given 部署请求不包含 sidecar 配置 When SandboxInstanceManager 构建 CR Then CR 与当前单容器行为一致
- [ ] **AC-003**：Given CR 下发到集群 When sandbox-controller 渲染 Pod Then Pod 包含主容器和 sidecar 容器，共享 network namespace

## 边界范围

### 本子需求包含

- SandboxInstance CR spec sidecars 字段设计
- SandboxInstanceManager 多容器构建逻辑
- sandbox_operator.py 中 sidecar 配置传递
- 相关单元测试

### 本子需求不包含

- 镜像构建/注册能力（子需求 2）
- create_ai_agent_app API 变更（子需求 3）
- sandbox-controller 渲染逻辑（controller 侧职责）
