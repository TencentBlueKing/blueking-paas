# 熵管理（Entropy Management）

> 目标：让系统"保持整洁"——通过自动化机制控制系统熵增速度，确保长期可维护。

## 1. 文档园艺机制

### 1.1 自动一致性检测

| 检测项 | 频率 | 方式 | 责任人 |
|-------|------|------|-------|
| 文档引用的文件路径是否存在 | 每次 PR | harness-gardening 扫描 | 自动化 |
| Harness 文档描述的模块结构与代码是否匹配 | 每周 / 结构变更后 | harness-gardening（含 dev-map 更新） | 平台团队 |
| REST API 文档与实际接口是否一致 | 每次接口变更 | drf-yasg 生成对比 | 平台团队 |
| CRD schema 双端一致（operator ↔ paas_wl） | 每次 CRD 变更 | 人工 Review + 生成对比 | 平台团队 |

### 1.2 园艺流程

1. 检测到不一致 → 记录差异（含具体路径/描述）
2. 简单不一致（路径变更、术语更新）→ Agent 自动提交修复
3. 复杂不一致（逻辑/架构变更）→ 通知责任人人工处理
4. 修复后更新一致性报告

## 2. 架构违规检测

### 2.1 检测策略

| 检测类型 | 触发时机 | 工具 | 阻断级别 |
|---------|---------|------|---------|
| 分层依赖违规 | PR 提交时（pre-commit） | import-linter（apiserver） | 阻断合并 |
| Go 规范违规 | PR 提交时（pre-commit） | golangci-lint（operator/sandbox/shim） | 阻断合并 |
| Python 类型错误 | PR 提交时（pre-commit） | mypy-apiserver | 阻断合并 |
| Python 代码规范 | PR 提交时（pre-commit） | ruff-check-fix / ruff-format / ruff-check | 阻断合并 |
| 敏感信息泄露 | PR 提交时（pre-commit） | 敏感信息检查 hook | 阻断合并 |
| 前端规范 | 提交/构建时 | ESLint / stylelint | 警告 |

> 所有检查由根目录 `.pre-commit-config.yaml`（`fail_fast: true`）统一编排，`pre-commit install` 后自动生效。

### 2.2 违规处理流程

- **阻断级别**：pre-commit / CI 失败，必须先修复才能提交/合并
- **警告级别**：允许合并，但记入技术债报告
- **报告级别**：仅记录，定期批量处理

## 3. 技术债追踪

### 3.1 追踪机制

| 债务类型 | 识别方式 | 记录位置 | 清理策略 |
|---------|---------|---------|---------|
| import-linter 豁免 | `.importlinter` 的 `ignore_imports` 条目 | 该文件注释已标注"待修复" | 逐步解耦，禁止新增豁免 |
| ruff 暂关规则 | `pyproject.toml` 中标注 TODO 的 `# 'DTZ'/'EM'/'PTH'/'UP'/'D'` 等 | pyproject.toml 注释 | 评估影响后逐项开启 |
| 旧版迁移代码 | `paasng.platform.mgrlegacy` | 模块自身 | 迁移完成后移除 |
| TODO/FIXME | 代码扫描 | Issue / 代码注释 | 每迭代 Review |
| 过时文档 | harness-gardening | 修复记录 | 发现即修复 |

### 3.2 技术债预算

- **不得扩大** `.importlinter` 的 `ignore_imports` 豁免范围（当前豁免为存量债务）
- 新增代码若引入技术债，必须在同 PR 中说明原因和计划清理时间
- ruff 中标注 TODO 的规则，全新模块建议直接遵循（不复用历史豁免）

## 4. 熵增度量

| 指标 | 计算方式 | 阈值 | 超标动作 |
|------|---------|------|---------|
| import-linter 豁免数 | `ignore_imports` 条目数 | 只减不增 | 拒绝新增豁免的 PR |
| Harness 文档一致性率 | 一致文档数 / 总文档数 | ≥ 95% | 触发集中修复 |
| pre-commit 通过率 | 首次通过 / 总提交 | 持续上升 | 排查高频失败项 |
| 技术债增速 | 每周新增 - 每周清理 | ≤ 0 | 暂停新功能，集中清理 |

## 检查清单

- [ ] 文档园艺检测机制已配置（harness-gardening）
- [ ] 架构违规检测已接入 pre-commit（import-linter / golangci-lint / mypy / ruff）
- [ ] 技术债追踪机制已建立（import-linter 豁免、ruff TODO 规则）
- [ ] 熵增度量指标和阈值已定义
- [ ] 各检测项有明确的责任人
