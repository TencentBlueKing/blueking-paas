# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

三类用户都可能，没有单一主用户：

- 蓝鲸开发者 / 产品经理：用自然语言快速搭出可跑的 SaaS
- 蓝鲸开发者：打样、验证想法，不一定上线
- 业务 / 运维人员：自己搭工具，少依赖开发

他们都是在蓝鲸运营系统 PaaS 里工作，要完成「从想法到一个蓝鲸 SaaS」这件事。

## Product Purpose

App-Spark 是蓝鲸运营系统 PaaS 推出的工具：用自然语言开发蓝鲸 SaaS。成功意味着用户能通过对话得到可部署的蓝鲸应用，而不是一份不能落地的代码草稿。

## Positioning

自然语言对话直接生成可部署的蓝鲸 SaaS，产品对象包含项目、会话和运行时。邻近产品（通用 AI 写代码、蓝鲸应用模板、低代码画布）可以生成代码或页面，但不能同样声称「在蓝鲸工作台里，对话即交付可部署 SaaS」。

## Operating Context

- 工作台产品，跑在蓝鲸统一登录与子应用路由（`@blueking/sub-saas`）里。
- 前端 `app-spark-ui`（Vue 3 + webpack），后端 `app-spark-api`。
- 已实现表面：首页项目列表 `/`、项目工作室 `/projects/:projectId`、Studio `/studio`。
- 项目工作室走真实会话与运行（对话 → Conversation → Run / SSE）；Studio 是 mock / 本地实验面。
- 本地开发：`app-spark-ui` 下 `npm run dev`，需蓝鲸登录与 API 代理。

## Capabilities and Constraints

- 中文优先，文案和界面按蓝鲸内部产品习惯。
- `/studio`（mock）保持原样，后续设计与实现不要改它。
- 除 Studio 以外的页面要求更美观；不强制使用 bkui-vue，可以用现有组件，也可以不用。
- 代码库当前使用 bkui-vue 与蓝鲸脚手架，这是实现现状，不是必须守住的视觉语言。
- 未决：是否对所有受众提供同一套工作流，还是按角色拆入口。

## Brand Commitments

- 产品名：App-Spark。
- 归属：蓝鲸运营系统 PaaS。
- 语气：内部工作台，中文，任务导向；不要写成对外营销落地页。

## Evidence on Hand

- 仓库根 `README.md` 对产品一句话定义。
- 可运行的首页、项目工作室、Studio 实现。
- 没有对外官网、客户证言、案例或媒体素材。未来工作不得编造用户、客户、指标或上线成果。

## Product Principles

1. 对话的终点是可部署的蓝鲸 SaaS，不是演示文稿或孤立代码块。
2. 服务多种使用者，但界面始终按内部工作台来写，不按营销站来写。
3. Studio 是隔离的实验面；真实项目面可以演进，Studio 不动。
4. 美观服务于把项目建起来、把会话跑起来，不服务于换一套品牌。
5. 没有证据的内容不要补；缺的素材留给用户提供。
