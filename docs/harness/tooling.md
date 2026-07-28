# 工具能力（Tooling）

> 目标：让 Agent "能行动"——封装标准化工具接口，保障执行稳定性。
> 本文档的 Skill/MCP/CLI 清单以 `.codebuddy/skills/harness-engineering/references/tool-dependencies.md` 为权威来源，环境状态来自本次规范生成时的实际检测。

## 1. 工具清单

### 1.0 Skill 清单与触发

> 扫描 `$SKILL_ROOT`（`.codebuddy/skills`）顶层 `*/SKILL.md`，并与 `tool-dependencies.md` 交叉验证后列出。用户额外安装但未登记的 Skill 不列入。

| Skill | 触发词（示例） | 功能概要 |
|-------|--------------|---------|
| tapd-product-discovery | 产品调研、PRD、原型、角色拆单 | PRD 前置的产品调研与角色故事拆分 |
| tapd-story-clarification | 需求澄清、clarify story | 提取"规划中"需求并多维度澄清、回写 TAPD |
| tapd-story-evaluation | 需求评估、需求拆分、RICE 评分 | 子需求拆分与价值/规模评分 |
| tapd-iteration-plan | 迭代规划、排迭代、创建迭代 | 基于依赖/规模/优先级将需求编排进迭代 |
| tapd-iteration-runner | 迭代执行、开发迭代、批量需求实现 | 批量调度一个迭代内全部需求的实现 |
| tapd-story-pipeline | 需求实现、开发需求 #ID、TDD 开发 | 单需求从澄清到代码提交的完整流水线 |
| tapd-bug-clarification | 缺陷澄清、根因分析 | 缺陷根因分析与丰富描述回写 |
| tapd-bug-evaluation | 缺陷评估、缺陷工时/规模 | 基于 PERT 的缺陷工时与规模评估 |
| code-review | 代码评审、code review | 代码质量、安全、可维护性评审 |
| bk-security-redlines | 安全红线、安全检查 | 蓝鲸代码安全三大红线检查 |
| go-micro-service | go-micro、grpc 服务、proto 接口 | go-micro 微服务开发（本项目非 go-micro，按需） |
| micro-service-project-init | 初始化微服务、项目脚手架 | go-micro v5 微服务项目框架生成（按需） |
| harness-engineering | Harness 规范、AI 治理规范、开发地图 | Harness 规范生成与文档园艺巡检 |
| graphify | 开发地图、知识图谱、代码索引 | 构建可查询的代码知识图谱（dev-map） |
| speckit-*（specify/plan/tasks/analyze/implement/checklist/constitution/clarify/taskstoissues/git-*） | Spec Kit 流程 | 规格驱动开发（需求→计划→任务→实现）各阶段 |

### 1.1 MCP 工具

> 以 `tool-dependencies.md` §一为权威来源；环境状态来自生成时检查。

| MCP 名称 | 所需接口 | 必需 | 环境状态 |
|---------|---------|------|---------|
| tapd（`tapd_taihu`） | `stories_get/create/update`、`iterations_get/create`、`bugs_get/update`、`tapd_id_get`、`tapd_field_detail_get` 等 | 是 | ✅ 已就绪（`stories_get` 验证成功） |

**维护规则：** 禁止在本节手写与 `tool-dependencies.md` 冲突的条目；变更先改权威清单再重新生成。

### 1.2 CLI 工具

| 工具 | 必需 | 检测条件 | 环境状态 |
|------|------|---------|---------|
| `git` | 是 | 始终 | ✅ 已就绪 |
| `bash` | 是 | 始终 | ✅ 已就绪 |
| `jq` | 是* | 始终（迭代报告 JSON 解析） | ✅ 已就绪 |
| `node` | 否 | `package.json` 存在（webfe） | ✅ 已就绪 |
| `go` | 否 | `go.mod` 存在（operator/bkpaas-cli/sandbox） | ❌ 未安装（涉及 Go 模块开发时需安装 ≥ 1.21） |
| `docker` / `python3` / `gh` | 否 | 按需 | 未主动检测，按需安装 |

> 微服务 go-micro 工具链（protoc 系列）：本项目 `go.mod` 不含 go-micro 依赖，**不适用**，无需检查。

### 1.3 配置文件

| 文件 | 必需 | 环境状态 |
|------|------|---------|
| `project.json`（`workspace_id`、`owner`） | 是 | ✅ 已就绪（`workspace_id`、`owner` 字段已配置） |

## 2. 工具接口规范

### 2.1 统一调用协议

- **输入**：结构化参数（JSON），区分必填/可选
- **输出**：统一 `{success, data, error}` 结构
- **错误**：明确错误码 + 可读错误信息
- MCP 工具调用遵循"先 `lookup_tapd_tool` 检索 → `lookup_tool_param_schema` 取参数 → `proxy_execute_tool` 执行"的三步协议

### 2.2 接口定义示例

```json
{
  "tool_name": "example_tool",
  "parameters": { "required": ["param1"], "optional": ["param2"] },
  "returns": { "success": "boolean", "data": "object", "error": "string|null" }
}
```

## 3. 稳定性保障

### 3.1 沙盒执行

| 执行环境 | 隔离方式 | 适用场景 |
|---------|---------|---------|
| Shell 沙盒 | 文件系统限制在项目目录内 | 日常命令执行 |
| dev_sandbox / sandbox daemon | 独立守护进程 | 应用开发沙箱操作 |
| Docker / kind 集群 | 容器隔离 | operator 测试、集成测试 |

### 3.2 容错策略

| 策略 | 配置 | 适用场景 |
|------|------|---------|
| 超时 | 所有外部调用设置超时 | MCP / HTTP / K8s API |
| 重试 | 最多 3 次，指数退避 | 网络请求、TAPD API |
| 幂等 | 相同参数多次调用结果一致 | 写操作、CRD 下发 |
| 降级 | 工具不可用时的备选 | graphify 缺失时跳过 dev-map |

### 3.3 敏感操作防护

| 操作类型 | 防护措施 |
|---------|---------|
| 删除文件/目录 | 二次确认 |
| 修改 git 配置 | 禁止擅自修改 |
| 强制推送 / 硬重置 | 需用户明确要求 |
| 访问生产环境 / 集群 | 严格禁止或需特殊授权 |
| 执行数据库迁移 | 审批 + 回滚方案 |
| CRD 下发到集群 | 经 operator 调和，禁止绕过 |

## 4. 工具扩展规范

1. 新增 Agent/Skill 依赖的工具，先更新权威清单 `tool-dependencies.md`（开发仓），再重新运行 harness-generating
2. 遵循"一个工具只做一件事"
3. 工具文档与代码同仓库版本控制

## 检查清单

- [ ] Skill 清单与 `$SKILL_ROOT` 顶层扫描结果一致（仅列 tool-dependencies 登记项）
- [ ] 所有标记为「必需」的工具已就绪（tapd MCP ✅、git/bash/jq ✅、project.json ✅）
- [ ] MCP 清单与 `tool-dependencies.md` 一致
- [ ] 外部调用配置了超时和重试策略
- [ ] 敏感操作有防护措施
