# 技术规范

> Agent 实现需求时的开发行为准则。根据需求涉及的端按需加载对应规范。

## 必选规范（所有项目强制）

| 分类 | 规范 | 文档 |
|------|------|------|
| 安全 | 蓝鲸代码安全三大红线 | [security-bk-redlines.md](security-bk-redlines.md) |
| 质量 | 代码评审规范（Google Code Review 指南） | [quality-code-review.md](quality-code-review.md) |

> 安全规范为横切关注点，**无论需求类型、技术栈如何，每次 Code Review 均须核查**。

## 当前项目选用的规范

| 分类 | 规范 | 文档 | 技术栈 |
|------|------|------|--------|
| 前端 | 前端开发规范（骨架，待完善） | [frontend-vue2.md](frontend-vue2.md) | Vue 2.7 + webpack + bk-magic-vue |
| 接口 | 接口协议规范（骨架，待完善） | [api-rest.md](api-rest.md) | REST(DRF) + K8s CRD + paas-service |
| 后端 | 后端开发规范·Python（骨架，待完善） | [backend-python-django.md](backend-python-django.md) | Python 3.11 + Django + DRF + Celery |
| 后端 | 后端开发规范·Go（骨架，待完善） | [backend-go-operator.md](backend-go-operator.md) | Go + kubebuilder / controller-runtime |

## Agent 加载策略

| 需求类型 | 应加载的规范 |
|---------|------------|
| 任何需求 | 安全规范 + 代码评审规范（必选） |
| 涉及前端页面（webfe） | frontend-vue2.md |
| 涉及 REST 接口 / CRD / 增强服务联调 | api-rest.md |
| 涉及 apiserver / svc-* 后端逻辑 | backend-python-django.md |
| 涉及 operator / bkpaas-cli / sandbox（Go） | backend-go-operator.md |
| 全栈需求 | 加载全部相关规范 |

## 规范约束力

- 标注"禁止"/"必须"的条目：**强制**遵守，违反需明确说明原因
- 标注"推荐"/"优先"的条目：**优先**遵守，有合理理由可偏离
- 常见场景参考：**参考**实现，可根据具体情况调整

## 章节快速索引

- **安全红线**：红线1 外部输入未校验 / 红线2 敏感接口未鉴权 / 红线3 敏感数据未加密 / 代码评审检查清单
- **代码评审**：核心原则 / 问题分级 / 检查维度（设计·功能·复杂度·测试·命名·规范·Git·安全·性能）/ 评分标准 / 报告格式
- **前端(Vue2)**：技术栈 / 项目结构 / 编码 / Vuex / 网络请求 / 组件 / UI / 安全 / 质量
- **接口(REST)**：REST(DRF) / K8s CRD / paas-service / 通用约束
- **后端(Python)**：分层架构 / DRF 接口 / Celery / 配置 / 日志 / 测试
- **后端(Go)**：结构与边界 / CRD / 编码 / 调和 / 测试 / 安全

## 待完善的规范

| 分类 | 当前状态 | 技术栈 | 如何完善 |
|------|---------|--------|---------|
| 前端 | 通用骨架（待补充） | Vue 2.7 + webpack | 编写完整 Vue2 规范 → 放入预设库 → 注册 index.yaml（vue2） |
| 接口 | 通用骨架（待补充） | REST(DRF) + CRD | 编写完整 REST/CRD 规范 → 放入预设库 → 注册 index.yaml（rest） |
| 后端 | 通用骨架（待补充） | Python/Django | 编写完整 Django 规范 → 放入预设库 → 注册 index.yaml（python-django） |
| 后端 | 通用骨架（待补充） | Go/kubebuilder | 编写完整 Operator 规范 → 放入预设库 → 注册 index.yaml（go-kubebuilder） |
