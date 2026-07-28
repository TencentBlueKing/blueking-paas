# 执行与验证（Execution & Verification）

> 目标：让 Agent "做对事"——通过执行循环和强制验证确保任务被正确完成。

## 1. Agent Loop 执行循环

### 1.1 循环结构

```
while 任务未完成:
    1. 观察（Observe）— 获取当前环境状态（代码、测试结果、TAPD 需求）
    2. 推理（Think）— 分析状态，规划下一步
    3. 行动（Act）— 调用工具执行操作（编辑代码、运行命令、调用 MCP）
    4. 验证（Verify）— 运行 pre-commit / pytest / make test 检查结果
    5. 更新（Update）— 更新任务状态与 TAPD 需求状态
```

本项目研发主线由 `workflow-agent` 按 [`docs/workflow.md`](../workflow.md) 驱动，迭代研发经 `tapd-iteration-runner` / `tapd-story-pipeline` 编排。

### 1.2 循环保护

| 保护机制 | 配置 | 触发动作 |
|---------|------|---------|
| 最大循环次数 | 按任务复杂度设定 | 终止并报告 |
| 无进展检测 | 连续多次状态无变化 | 暂停并请求人工介入 |
| 修复失败上限 | 连续修复失败达阈值 | 暂停并请求人工介入 |
| Token 预算 | 视上下文窗口 | 警告并简化后续操作 |

## 2. 强制验证机制

### 2.1 预完成检查清单

Agent 在宣称任务完成前，必须逐项确认：

| 检查项 | 验证方式 | 跳过条件 |
|-------|---------|---------|
| Python 代码规范/类型 | `ruff check` + `mypy`（或 `pre-commit run -a`） | 无 Python 变更 |
| 分层依赖合规 | import-linter（pre-commit） | 无 apiserver 变更 |
| Go 规范与编译 | `make lint`（golangci-lint） | 无 Go 变更 |
| 前端规范 | `npm run lint` | 无 webfe 变更 |
| 后端测试通过 | `pytest --reuse-db`（apiserver/paasng） | 无相关变更 |
| operator 测试通过 | `make test`（ginkgo/gomega） | 无 operator 变更 |
| 对照任务 Spec | 逐条检查需求点（TAPD story） | 无 |
| 文档已同步更新 | 检查关联文档（含 Harness/API 文档） | 无文档影响 |

### 2.2 验证失败处理

- 验证失败 → 自动回到执行循环修复
- 连续多次修复失败 → 暂停并请求人工介入
- 验证结果记录到执行日志

## 3. 任务漂移检测

| 信号 | 含义 | 处理方式 |
|------|------|---------|
| 处理 Spec 以外的任务 | 任务漂移 | 回退到最近检查点 |
| 修改与任务无关的模块 | 范围蔓延 | 撤销变更并提醒 |
| 自主改变技术方案/架构分层 | 决策越权 | 暂停并请求确认 |
| 循环执行相同操作 | 陷入死循环 | 终止并报告 |
| 新增 `.importlinter` 豁免以"绕过"报错 | 违反熵管理约束 | 阻止并要求按分层重构 |

检查点机制：每完成一个子任务（子需求/子任务）设置检查点，记录任务状态、已完成项、待完成项；漂移时回退到最近检查点。

## 4. 结果可观测性

### 4.1 执行日志

每次任务执行应记录：task_id、timestamp、action、input、output、duration_ms、tokens_used、status（success/failure/skipped）。

### 4.2 可观测性数据源

| 分析维度 | 工具 | 用途 |
|---------|------|------|
| 应用运行日志 | 蓝鲸日志（bk_log） | 定位运行时异常 |
| 性能指标 | 蓝鲸监控 / Prometheus（django-prometheus、operator metrics） | 性能与容量分析 |
| 链路追踪 | svc-otel（APM） | 跨服务调用分析 |
| Token 消耗分布 | Agent 执行日志 | 优化 Prompt 效率 |

### 4.3 指标看板

| 指标 | 计算方式 | 目标值 |
|------|---------|-------|
| 任务完成率 | 成功任务 / 总任务 | ≥ 95% |
| 首次验证通过率 | 首次通过 / 总验证 | ≥ 90% |
| pre-commit 一次通过率 | 一次通过 / 总提交 | 持续上升 |
| Token 效率 | 有效操作 / 总 Token | 持续上升 |

## 检查清单

- [ ] Agent Loop 执行循环已定义（含 workflow-agent 驱动）
- [ ] 循环保护机制已配置
- [ ] 预完成检查清单已制定（覆盖 ruff/mypy/import-linter/golangci-lint/pytest/ginkgo）
- [ ] 任务漂移检测规则已明确
- [ ] 执行日志格式和存储方案已确定
- [ ] 关键指标和目标值已定义
