# Harness Engineering 规范

> 本目录定义了项目的 AI Agent 运行环境规范，是 Agent 理解项目边界、工具能力和行为约束的唯一来源。

## 项目概述

- **项目名称**：蓝鲸智云 PaaS 平台 - 开发者中心（Blueking PaaS）
- **技术栈**：Python 3.11 / Django 5.2 / DRF / Celery（apiserver、svc-*）、Go / kubebuilder / controller-runtime（operator）、Go / cobra（bkpaas-cli、sandbox）、Vue.js 2 / bk-magic-vue / webpack（webfe）
- **Agent 适用场景**：TAPD 迭代研发流水线、需求澄清与评估、代码评审与安全检查、缺陷澄清与评估、Harness 规范生成与巡检

## 规范导航

| 组件 | 文档 | 概要 |
|------|------|------|
| 上下文工程 | [context-engineering.md](context-engineering.md) | 知识来源、上下文结构、动态数据接入 |
| 架构约束 | [architectural-constraints.md](architectural-constraints.md) | 分层模型、依赖规则、Linter 规则 |
| 熵管理 | [entropy-management.md](entropy-management.md) | 文档园艺、技术债追踪、一致性检测 |
| 工具能力 | [tooling.md](tooling.md) | Skill 清单、MCP/CLI 工具、稳定性保障 |
| 执行与验证 | [execution-verification.md](execution-verification.md) | 执行循环、验证清单、可观测性 |

## 使用说明

1. Agent 首次接触项目时，先读本文件获取全局视图
2. 执行具体任务时，按需深入阅读对应组件文档
3. 规范更新后需同步检查关联组件的一致性

## 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-07-28 | 初始版本 |
