# ESLint 历史问题治理方案

> 适用范围：`webfe/package_vue`（PaaS 3.0 前端主工程）
> 编写日期：2026-09-01
> 当前分支：`upgrade-v1`（与 upstream/main 同步）

---

## 一、背景与问题规模

对 `webfe/package_vue` 执行全量 eslint 检查的结果：

| 指标 | 数值 |
|---|---|
| 存在问题的文件数 | 421 |
| 问题总数 | **12,499** |
| error 数 | 2,667 |
| warning 数 | 9,832 |
| 可被 `--fix` 自动修复 | 11,381（91%） |

问题按规则分布（Top 10）：

| 规则 | 数量 | 类别 |
|---|---|---|
| `indent` | 5,164 | 格式（可自动修复） |
| `linebreak-style` | 1,791 | 换行符 |
| `comma-dangle` | 1,155 | 格式（可自动修复） |
| `vue/html-indent` | 876 | 格式（可自动修复） |
| `arrow-parens` | 556 | 格式（可自动修复） |
| `no-param-reassign` | 521 | 代码质量（warning） |
| `space-before-function-paren` | 410 | 格式（可自动修复） |
| `no-trailing-spaces` | 383 | 格式（可自动修复） |
| `no-unused-vars` | 188 | 代码质量（error） |
| `function-paren-newline` | 174 | 格式（可自动修复） |

---

## 二、根因分析

三个原因叠加：

1. **存量代码从未按现行规则全量格式化（主因）**
   - eslint 规则从 2023 年的 `standard` 风格演进为 `@blueking/eslint-config-bk@2.1.0`（2 空格缩进、强制尾逗号等），规则持续收紧；
   - 存量代码仍为旧风格（4 空格缩进、无尾逗号），规则收紧后全部转为告警；
   - `package.json` 中 `lint` 脚本（`eslint --fix`）仅在手动运行时生效，CI 无全量 lint 门禁；
   - 上游提交 `509461bcd`（2026-08-26「修复 lint 问题 #3021」）仅修复了十几个文件的 error，未清理历史 warning 基线。

2. **13 个文件混合换行符**
   - 这些文件 CRLF 与 LF 各占约一半（Windows 编辑器编辑后入库），eslint 规则要求 LF；
   - 仓库 `core.autocrlf=false`，CRLF 已被提交进仓库，产生 1,791 个告警。

3. **`apiserver/.eslintrc.js` 为遗留"死配置"**
   - 该配置引用 `babel-eslint`、`standard`、`eslint-plugin-html`，但对应依赖**均未安装**；
   - 前端源码早已迁移至 `webfe/`，此配置若被 IDE ESLint 插件拾取（工作区为仓库根目录时会向上匹配），会对 `apiserver/` 下 js 文件产生大量解析错误。

---

## 三、治理目标

- 全量 lint 问题从 12,499 降至 0（或按团队决策豁免部分规则）；
- CI 建立 lint 门禁，阻断新增问题；
- 统一换行符与编辑器行为，杜绝环境差异导致的重复告警。

---

## 四、分步实施方案

### 阶段 0：固定 lint 工具链版本（已执行，2026-09-01）

**背景**：`package.json` 原声明 `"@blueking/eslint-config-bk": "^2.1.0-beta.12"`，caret 范围导致实际安装了 2.1.0 正式版。经对比，beta.12 → 2.1.0 期间底层规则引擎发生多次 major 级变化：

```
eslint:                     ^8.14.0 -> ^8.57.0
eslint-plugin-vue:          ^8.7.1  -> ^9.23.0   (major)
@typescript-eslint/*:       ~5.20.0 -> ^7.2.0    (跨 2 个 major)
@vue/eslint-config-standard: ~6.1.0 -> ^8.0.1    (跨 2 个 major)
eslint-config-tencent:      ^1.0.4  -> (移除)
```

规则集随版本漂移而变化，是历史告警涌现的技术推手之一；不固定版本，治理基线随时可能再次失效。

**已执行操作**：
1. `package.json` 中改为精确版本 `"@blueking/eslint-config-bk": "2.1.0"`；
2. 执行 `npm install`，`package-lock.json` 已同步锁定 2.1.0；
3. 复跑全量 lint 验证基线：**12,499 个问题（2,667 errors + 9,832 warnings）**，与固定前完全一致，基线可复现。

**暂不升级到 3.x / ESLint 9 的理由**：
- 本地 Node 为 v14.17.6，ESLint 9 要求 Node ≥18.18，存在硬性环境阻塞；
- `@blueking/eslint-config-bk@3.0.0` 尚处 beta 阶段，且 3.x 面向 flat config（`.eslintrc.js` → `eslint.config.js` 迁移）；
- 升级会再次改变规则基线，与当前治理目标冲突。正确顺序：**固定基线 → 清零问题 → 再独立排期升级**（升级前需先完成 Node ≥18 工具链升级）。

**遗留事项**：
- `package-lock.json` 为 lockfileVersion 1（npm 6 生成），建议后续用与 CI 一致的 npm 版本重新生成 v3 格式，CI 中使用 `npm ci` 安装；
- `npm install` 报告 180 个依赖漏洞（4 critical），属历史老依赖链问题，建议另立专项处理，不在本方案范围内。

### 阶段 1：消除配置噪音（✅ 已完成，2026-09-01）

**步骤 1.1 删除死配置（已执行）**
- 已删除 `apiserver/.eslintrc.js`（其引用的 `babel-eslint`、`standard`、`eslint-plugin-html` 均未安装，前端已迁移至 `webfe/`）；
- 若 IDE 工作区为仓库根目录，建议在 ESLint 插件设置中将 lint 范围限定为 `webfe/package_vue`。

**步骤 1.2 统一换行符（已执行，13 个文件 CRLF → LF）**

实际转换文件清单：
- `src/api/index.js`
- `src/components/searching/searchDocList.vue`、`selectEventMixin.vue`
- `src/components/ui/Qrcode.vue`
- `src/views/dev-center/app/create-cloud-module/comps/git-extend.vue`
- `src/views/dev-center/app/create-module/comps/git-extend.vue`
- `src/views/dev-center/app/engine/deployment/comps/deploy-log/` 下 6 个文件（`index.vue`、`render-skip-stage.vue`、`render-stage.vue`、`deploy-stage/index.vue`、`deploy-stage/render-process-item.vue`、`deploy-stage/render-status-item.vue`）
- `src/views/dev-center/app/engine/entry-config/comps/mobile-config.vue`

**验收结果**：转换后文件 `linebreak-style` 告警归零（剩余匹配为 `operator-linebreak`，属阶段 2 格式修复范畴）。预计全量告警降至约 10,700。

### 阶段 2：全量自动修复（机械操作，一次提交）

**步骤 2.1 执行自动修复**

```powershell
cd d:\Github_Project\bk-paas\webfe\package_vue
npm run lint   # 即 eslint --fix --ext .js,.vue src
```

预计消除 11,381 个问题（91%）。

**步骤 2.2 验证修复未破坏功能**
- 自动修复仅涉及格式，但需执行一次完整构建确认：
  `npm run build:ce`
- 重点抽查 `vue/html-indent` 修复的 `.vue` 文件模板区域，确认渲染正常。

**步骤 2.3 独立提交**
- 本次提交**只包含格式化改动，不混杂任何业务逻辑修改**，便于 review 与回滚；
- 提交信息建议：`style: 全量格式化，修复 eslint 历史格式问题（11,381 项）`。

**验收标准**：问题数降至约 1,100；`git diff` 仅含空白/引号/缩进类变化。

### 阶段 3：剩余问题逐类处置（约 1,100 项）

**步骤 3.1 按类别分批处理**

| 类别 | 规则（数量） | 处置建议 |
|---|---|---|
| 未使用变量 | `no-unused-vars`（188） | 删除无用变量/导入；保留语义的参数改 `_` 前缀 |
| 属性命名 | `vue/attribute-hyphenation`（89）、`camelcase`（70） | 逐个改为连字符/驼峰命名 |
| 行长度 | `max-len`（85） | 手工换行 |
| 参数再赋值 | `no-param-reassign`（521，warning） | Vue 2 生态常见，建议**团队决策**：修复或关闭该规则 |
| 其他零散 | `no-restricted-syntax`（67）、`arrow-body-style`（66）、`prefer-destructuring`（50）等 | 逐个评估 |

**步骤 3.2 团队规则决策会议（一次性）**
- 对 `no-param-reassign` 等争议规则统一去留，决策结果落入 `.eslintrc.js`，避免反复；
- 决策后剩余问题分模块（`views/`、`components/`、`store/`、`api/`）认领修复，每模块独立提交。

**验收标准**：`npx eslint --ext .js,.vue src` 输出为空（或仅剩已豁免规则的豁免声明）。

### 阶段 4：建立防再犯机制

**步骤 4.1 添加 `.editorconfig`**（仓库根目录）

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true

[*.{js,vue}]
indent_style = space
indent_size = 2
```

**步骤 4.2 Git 换行符策略**
- 仓库添加 `.gitattributes`：`* text=auto eol=lf`，从源头杜绝 CRLF 入库。

**步骤 4.3 提交前增量 lint（husky + lint-staged）**

```powershell
npm i -D husky lint-staged
```

```json
"lint-staged": {
  "src/**/*.{js,vue}": ["eslint --fix --max-warnings 0"]
}
```

只校验改动文件，不阻塞历史代码。

**步骤 4.4 CI lint 门禁**

```yaml
# CI 流水线增加
- run: cd webfe/package_vue && npx eslint --ext .js,.vue src --max-warnings 0
```

**验收标准**：本地提交含 lint 问题的代码会被拦截；CI 对全量代码执行零容忍检查。

---

## 五、实施节奏与里程碑

| 阶段 | 预估工作量 | 产出 | 风险 |
|---|---|---|---|
| 阶段 0 | ✅ 已完成（0.5 天） | 版本固定为 2.1.0，基线 12,499 可复现 | 已消除（版本漂移） |
| 阶段 1 | ✅ 已完成（0.5 天） | 死配置已删、换行符已统一 | 极低（已验收通过） |
| 阶段 2 | 0.5 天 + 构建验证 | 告警降至 ~1,100 | 低（格式化需构建验证） |
| 阶段 3 | 2~4 人日（可并行分模块） | 告警归零 | 中（涉及代码语义，需 review） |
| 阶段 4 | 0.5 天 | 门禁与钩子生效 | 低 |

**总体原则**：
- 每阶段独立提交、独立可回滚；
- 格式化提交与逻辑修改严格分离；
- 阶段 3 完成前，阶段 4 的 CI 门禁可先以 `--max-warnings <当前基线值>` 的递减策略灰度上线，避免长期分支被门禁卡死。

---

## 六、风险与回滚

| 风险 | 应对 |
|---|---|
| `--fix` 对 `.vue` 模板的 `html-indent` 修复影响渲染 | 构建验证 + 抽查关键页面；异常时 revert 单个文件 |
| 大量格式化提交引发 merge 冲突 | 治理期间与 upstream 同步前先执行本方案；冲突以本仓库格式化结果为准 |
| 换行符转换导致 git 全文件重写 | 仅涉及 13 个混合换行文件，范围可控 |
