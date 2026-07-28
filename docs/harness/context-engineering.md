# 上下文工程（Context Engineering）

> 目标：让 Agent "知道该知道的信息"——确保 Agent 在任务执行中能获取准确、及时、适量的上下文。

## 1. 知识来源定义

### 1.1 唯一知识来源（Single Source of Truth）

| 知识类型 | 存储位置 | 维护责任人 | 更新频率 |
|---------|---------|-----------|---------|
| 项目入口与全貌 | `AGENTS.md` | 平台团队 | 结构变更时 |
| 架构设计图 | `docs/resource/img/architecture-*.png`、`README.md` | 平台团队 | 架构变更时 |
| 本地开发指引 | `docs/DEVELOP_GUIDE.md` | 平台团队 | 环境变更时 |
| 贡献流程 | `docs/CONTRIBUTING.md` | 平台团队 | 流程变更时 |
| 需求文档 | `docs/reqs/` | 平台团队 | 需求变更时 |
| 子模块设计约定 | `apiserver/AGENTS.md`、`apiserver/design_notes/`、`sandbox/daemon/AGENTS.md` | 平台团队 | 模块变更时 |
| 分层依赖契约 | `apiserver/paasng/.importlinter` | 平台团队 | 分层调整时 |
| Harness 规范 | `docs/harness/` | 平台团队 | 规范变更时 |
| 词汇表 | `docs/glossary.md` | 平台团队 | 新术语出现时 |
| 安全规范 | `docs/standards/security-bk-redlines.md` | 平台团队 | 规范变更时 |
| 代码评审规范 | `docs/standards/quality-code-review.md` | 平台团队 | 规范变更时 |
| 前端规范 | `docs/standards/frontend-vue2.md` | 平台团队 | 技术栈/规范变更时 |
| 开发地图 | `docs/dev-map/` | 平台团队 | 代码结构变更时 |

### 1.2 禁止的知识来源

以下渠道的信息不应作为 Agent 决策依据（容易过时或缺乏版本控制）：
- 即时通讯记录（企业微信、QQ 群等）
- 未纳入版本控制的外部 Wiki
- 口头约定或会议记录

## 2. 渐进式上下文披露

### 2.1 三层结构

```
第一层（入口）：AGENTS.md（≤100 行）
  ├── 项目概述与架构（控制面/数据面）
  ├── 目录结构（二级）
  ├── 关键命令（pre-commit / pytest / make / npm）
  └── 导航索引（指向 docs/harness、docs/standards、docs/dev-map）

第二层（导航）：docs/harness/README.md、docs/standards/README.md
  ├── 五大组件规范导航
  ├── 技术规范导航与加载策略
  └── 各文档控制在合理长度

第三层（详情）：各组件文档 + 子模块 AGENTS.md + 代码内注释 + dev-map 图谱
  └── 仅在需要时访问，不主动全量加载到上下文
```

### 2.2 上下文预算管理

- Agent 的上下文窗口视为有限资源，需精心管理
- 优先加载与当前任务直接相关的模块文档（如改 operator 只读 `operator/` 相关）
- 大文件（如 `apiserver/pyproject.toml` 的 ruff 配置）通过索引定位相关段落，避免全量加载
- 跨模块任务借助 `docs/dev-map/graph.json` 定位关联，而非逐文件扫描

## 3. 动态上下文接入

### 3.1 实时数据源

| 数据源 | 接入方式 | 用途 | 刷新频率 |
|-------|---------|------|---------|
| TAPD | MCP（`tapd_taihu`，见 tooling.md） | 需求/缺陷/迭代拉取与回写 | 实时 |
| Git 仓库 | `git` CLI | 变更范围、历史、分支 | 实时 |
| 知识图谱 | `docs/dev-map/graph.json`（graphify） | 代码结构与概念关联查询 | 代码变更后更新 |

### 3.2 可观测性数据

| 数据类型 | 工具 | 访问方式 |
|---------|------|---------|
| 应用日志 | 蓝鲸日志平台（bk_log）/ ELK | 平台查询 <!-- TODO: 待补充访问细节 --> |
| 性能指标 | 蓝鲸监控（bkmonitorv3）/ Prometheus（django-prometheus、operator metrics） | 平台查询 <!-- TODO: 待补充 --> |
| 链路追踪 | svc-otel（OpenTelemetry/APM） | 平台查询 <!-- TODO: 待补充 --> |

## 4. 上下文更新机制

### 4.1 触发条件

- 代码架构发生重大变更（新增模块、调整 `.importlinter` 分层）
- REST API 接口新增或变更（drf-yasg 生成的接口文档需同步）
- CRD schema 变更（operator `api/v1alpha2/bkapp_types.go` 与 apiserver `paas_wl` 需同步）
- 需求文档更新（`docs/reqs/`）
- 依赖的外部系统（增强服务协议、蓝鲸周边）发生变更

### 4.2 更新流程

1. 变更方在 PR 中同步更新相关文档
2. Code Review 时检查文档是否同步更新（见 `docs/standards/quality-code-review.md`）
3. 文档园艺（harness-gardening）定期扫描检测遗漏

## 检查清单

- [ ] 所有知识类型都有明确的存储位置和维护责任人
- [ ] AGENTS.md 控制在 100 行以内
- [ ] 动态数据源（TAPD / Git / dev-map）已配置接入方式
- [ ] 上下文更新机制已建立并有人负责
