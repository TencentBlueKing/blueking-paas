# 前端开发规范（Vue 2.7 + webpack）

<!--
  harness-preset: 降级生成（Level 2）。预设库仅有 Vue 3 预设（frontend-vue3.md），
  与本项目实际技术栈（Vue 2.7 + webpack + bk-magic-vue）不符，故基于 frontend-generic.md
  骨架结合项目实际生成。如需完善为完整规范，可编写后放入
  skills/harness-engineering/assets/standards/ 并在 index.yaml 注册 vue2 预设。
-->

> 适用于 `webfe/package_vue` 单页应用。技术栈：Vue 2.7（Options API 为主）+ @blueking/cli-service-webpack（webpack）+ bk-magic-vue + Vuex + Vue Router + axios。

---

## 一、技术栈要求

| 技术 | 版本要求 | 用途 |
|------|---------|------|
| Vue | 2.7.x | 视图框架（Options API，可用 `<script setup>` 兼容语法需谨慎） |
| bk-magic-vue | ^2.5.x | 蓝鲸 Magic UI 组件库（Vue 2 版本） |
| Vuex | 项目内置 | 全局状态管理 |
| Vue Router | 项目内置 | 路由 |
| axios | 1.x | HTTP 请求 |
| 构建 | @blueking/cli-service-webpack（webpack） | 开发/构建（`dev:ce/ee/te`、`build`） |
| Lint | @blueking/eslint-config-bk + @blueking/stylelint-config-bk | ESLint（`.js,.vue`）+ Stylelint |

> 注意：本项目**非** Vite/Pinia/TypeScript-first，请勿套用 Vue 3 Composition API / Pinia 规范。

---

## 二、项目结构

以 `webfe/package_vue/src` 实际结构为准，按功能而非文件类型组织：

```
src/
├── api/                  # 网络请求封装（基于 axios）
├── components/           # 公共组件
├── views/ | pages/       # 页面组件（按模块分目录）
├── router/               # 路由配置
├── store/                # Vuex 状态管理
├── common/ | utils/      # 工具函数
├── css/                  # 全局样式
└── main.js               # 应用入口
```

<!-- TODO: 按 webfe/package_vue/src 实际目录补全 -->

---

## 三、编码规范

### 3.1 通用原则

- 组件默认使用 **Options API**（`data/computed/methods/watch/生命周期`），顺序固定
- 多版本构建通过 `BK_APP_VERSION`（ce/ee/te）区分，版本差异代码集中管理
- 提交前执行 `npm run lint` 修复 ESLint 问题

### 3.2 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `UserList.vue` |
| 工具函数 | camelCase | `formatDate.js` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| CSS class | kebab-case | `.page-header` |

---

## 四、状态管理规范（Vuex）

- 全局状态集中在 `store/`，按模块拆分 module（`namespaced: true`）
- 组件内局部状态优先用组件 `data`，跨组件共享才提升到 Vuex
- 异步请求逻辑封装在 actions 中，mutations 只做同步状态变更
- 禁止在组件中直接修改 `this.$store.state`，必须经 mutation

---

## 五、网络请求规范

- 所有请求通过 `src/api/` 统一封装的 axios 实例发起，禁止直接 `axios(...)`
- 响应拦截器统一处理：数据剥壳、错误提示、401 跳转登录
- 请求超时、重试策略统一配置

<!-- TODO: 补充 axios 实例封装的实际约定 -->

---

## 六、组件设计原则

| 场景 | 推荐方案 |
|------|---------|
| 父 → 子 | Props |
| 子 → 父 | `$emit` 事件 |
| 跨层级 | Vuex 或 provide/inject |
| 兄弟组件 | 提升状态到共同父组件 |

- 优先使用 bk-magic-vue 组件，避免重复造轮子与裸原生元素

---

## 七、UI 与样式规范

| 原则 | 说明 |
|------|------|
| 组件库优先 | 使用 bk-magic-vue 组件 |
| 样式隔离 | 组件样式使用 `scoped` 或 BEM 命名 |
| 国际化 | 文案走 i18n，避免硬编码中文 |

---

## 八、安全（前端红线，详见 quality-code-review §3.8）

- 禁止 `v-html` 渲染未净化的用户输入（XSS，SEC-001）
- Token 不存 localStorage 长效凭证，不出现在 URL query（SEC-004/SEC-005）
- 权限不能仅依赖前端控制，服务端必须再校验（SEC-006）

---

## 九、质量保证

### 9.1 提交前自验

```bash
cd webfe/package_vue
npm run lint          # ESLint (.js,.vue) 自动修复
# npm run build:ce    # 构建验证（按版本）
```

### 9.2 代码审查清单

- [ ] 网络请求通过统一 axios 封装
- [ ] Vuex 状态变更经 mutation
- [ ] 组件优先使用 bk-magic-vue
- [ ] 无 `v-html` XSS 风险
- [ ] 定时器/监听器在 `beforeDestroy` 清理
- [ ] 路由懒加载（`() => import(...)`）
- [ ] 大列表分页或虚拟滚动

---

## 十、常见陷阱

| # | 陷阱 | 规避 |
|---|------|------|
| 1 | Vue 2 响应式对新增对象属性无感 | 使用 `this.$set` |
| 2 | 数组索引赋值不触发更新 | 使用 `splice` / `$set` |
| 3 | 组件卸载未清理定时器/监听 | `beforeDestroy` 中清理 |
| 4 | int64 精度丢失 | API 层转字符串处理 |
| 5 | 误用 Vue 3 语法 | 本项目为 Vue 2.7，核对 API 兼容性 |
