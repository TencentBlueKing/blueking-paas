# 词汇表（Glossary）

> 本项目涉及的核心概念、术语和缩写定义。Agent 和人类成员均以此为术语的唯一解释来源。

## Harness Engineering 核心概念

| 术语 | 英文 | 定义 |
|------|------|------|
| 驾驭工程 | Harness Engineering | 为 AI Agent 构建可靠运行环境的方法论，由上下文工程、架构约束、熵管理、工具能力、执行与验证五大组件构成 |
| 上下文工程 | Context Engineering | 确保 Agent 在任务执行中获取准确、及时、适量上下文的机制（知识来源、渐进式披露、动态数据接入） |
| 架构约束 | Architectural Constraints | 通过刚性规则（分层依赖、Linter）确保代码结构一致性与可维护性 |
| 熵管理 | Entropy Management | 通过自动化机制控制系统熵增速度，保障长期可维护（文档园艺、违规检测、技术债追踪） |
| 工具能力 | Tooling | 封装标准化工具接口（Skill/MCP/CLI），保障 Agent 执行的稳定性 |
| 执行与验证 | Execution & Verification | 通过执行循环与强制验证确保任务被正确完成 |
| 渐进式上下文披露 | Progressive Disclosure | 三层文档结构：AGENTS.md（入口）→ harness/README.md（导航）→ 组件文档（详情） |

## 架构与设计模式

| 术语 | 英文 | 定义 |
|------|------|------|
| 控制面 | Control Plane | apiserver（Python/Django），负责应用创建、开发、部署、管理的业务编排 |
| 数据面 | Data Plane | operator（Go/kubebuilder），watch CRD 并调和为实际 K8s 资源 |
| 声明式交互 | Declarative Interaction | apiserver 通过下发 CRD 与 operator 间接交互，禁止直接 RPC |
| 分层单向依赖 | Layered Dependency | 依赖只能向下流动，高层可依赖低层，低层不得引用高层 |
| 桥接层 | Bridge Layer | `paas_wl`，位于 apiserver 与 Kubernetes 之间，定义 CRD 客户端并生成/下发 manifest |
| Parse, Don't Validate | Parse, Don't Validate | 在系统边界处将原始数据解析为强类型模型，后续代码只操作解析后的类型 |
| 架构决策记录 | ADR (Architecture Decision Record) | 记录架构决策背景/选择/后果的文档，存放于 `docs/adr/` |
| 增强服务插拔协议 | paas-service | svc-* 增强服务与 apiserver 交互的统一 HTTP/REST 协议，支持插拔 |

## Skill 相关术语

| 术语 | 英文 | 定义 |
|------|------|------|
| Skill | Skill | Agent 可调用的领域能力扩展包，位于 `$SKILL_ROOT/<name>/SKILL.md` |
| 技能根目录 | $SKILL_ROOT | Skill 存放根目录，本项目为 `.codebuddy/skills` |
| 项目领域 | $PROJECT_DOMAIN | 项目类型标识，本项目为 `code-project` |
| 规格驱动开发 | Spec Kit | speckit-* 系列 Skill 实现的需求→计划→任务→实现流程 |
| 文档园艺 | Doc Gardening | 定期扫描并修复文档与代码不一致的机制 |

## 工具与平台

| 术语 | 英文/缩写 | 定义 |
|------|----------|------|
| 模型上下文协议 | MCP (Model Context Protocol) | Agent 调用外部工具的标准协议，本项目接入 tapd（`tapd_taihu`） |
| TAPD | TAPD | 腾讯敏捷研发协作平台，用于需求/缺陷/迭代管理 |
| 知识图谱 | graphify | 构建可查询的代码知识图谱（dev-map），支持结构与概念关联查询 |
| import-linter | import-linter | Python 分层依赖契约工具，配置于 `apiserver/paasng/.importlinter` |
| golangci-lint | golangci-lint | Go 静态检查工具，配置于 `operator/.golangci.yaml` |
| ruff | ruff | Python 代码检查/格式化工具（line-length 119, py311） |
| pre-commit | pre-commit | 提交前检查框架，统一编排 ruff/mypy/import-linter/golangci-lint |

## 工程实践术语

| 术语 | 英文 | 定义 |
|------|------|------|
| Agent 执行循环 | Agent Loop | 观察→推理→行动→验证→更新的循环执行模型 |
| 预完成检查清单 | Pre-completion Checklist | 宣称任务完成前必须逐项确认的验证清单（编译/测试/Lint/Spec 对照/文档同步） |
| 任务漂移 | Task Drift | Agent 偏离任务 Spec、范围蔓延或决策越权的现象 |
| 检查点 | Checkpoint | 记录任务状态的还原点，漂移发生时可回退 |
| 技术债 | Technical Debt | 循环依赖、死代码、过时文档、TODO/FIXME 等待偿还项 |
| 分层豁免 | ignore_imports | `.importlinter` 中对未解耦模块的临时依赖豁免，属待偿还技术债，不得扩大 |

## 信号协议

| 术语 | 格式 | 定义 |
|------|------|------|
| Linter 错误信息 | `[规则编号] 违反...：<位置>\n修复方式：...\n参考文档：...` | 直接包含修复指引，供 Agent 自主修复 |
| MCP 三步调用 | `lookup_tapd_tool` → `lookup_tool_param_schema` → `proxy_execute_tool` | tapd MCP 工具的检索→取参→执行调用协议 |
| 工具返回结构 | `{success, data, error}` | 自定义工具统一的结构化输出 |

## 项目业务术语

| 术语 | 英文/缩写 | 定义 |
|------|----------|------|
| 蓝鲸 PaaS | BlueKing PaaS | 开放式 SaaS 应用开发平台，提供应用创建/开发/部署/管理能力 |
| 开发者中心 | Developer Center | apiserver 承载的核心后端，含 paasng 业务层与 paas_wl 工作负载桥接层 |
| BkApp | BkApp | 云原生应用 CRD（`operator/api/v1alpha2`），描述应用的声明式期望状态 |
| 增强服务 | Enhanced Service (svc-*) | 通过 paas-service 协议插拔的能力（svc-bkrepo/mysql/rabbitmq/otel） |
| 多租户 | Tenant | `paasng.core.tenant` 提供的租户隔离能力 |
| 版本区域 | Region | `paasng.core.region` 提供的部署环境版本区域划分 |
| 开发沙箱 | dev_sandbox / sandbox daemon | 供应用在线开发的独立守护进程 |
| 应用模块 | Module | 应用下的可独立部署单元（`paasng.platform.modules`） |

---

*持续补充中——遇到新术语时请直接在对应分类下添加。*
