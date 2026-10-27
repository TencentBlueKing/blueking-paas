---
name: "App-Spark Formal Workbench"
description: "面向蓝鲸内部用户、以对话贯通项目创建到可部署应用预览的连续工作台系统。"
colors:
  ink: "#12141a"
  muted: "#5c6573"
  faint: "#88919e"
  line: "#e4e9f1"
  canvas: "#fff"
  surface: "#fff"
  subtle-bg: "#f5f7fa"
  hover-bg: "#e8ecf3"
  accent: "#3d6dff"
  accent-soft: "#eef2ff"
  accent-focus: "#8ea2ff"
  check: "#2f5bff"
  live: "#3d8f6a"
  danger: "#e5484d"
  danger-hover: "#d13b40"
  danger-soft: "#fff1f1"
  publish: "#5b3fd6"
  publish-soft: "#efeaff"
  warning: "#b26b00"
  warning-soft: "#fff4e0"
  bk-primary: "#3a84ff"
  bk-primary-hover: "#1768ef"
  nav-bg: "#182132"
  nav-text: "#dcdee5"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(30px, 4.2vw, 44px)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  mono:
    fontFamily: "Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
rounded:
  xs: "6px"
  sm: "8px"
  field: "9px"
  md: "10px"
  toolbar: "12px"
  surface: "14px"
  composer: "16px"
  prominent: "20px"
  pill: "999px"
spacing:
  micro: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  2xl: "32px"
  3xl: "40px"
  4xl: "56px"
components:
  button-primary:
    backgroundColor: "{colors.bk-primary}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "0 16px"
    height: "36px"
  button-primary-hover:
    backgroundColor: "{colors.bk-primary-hover}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
  button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.sm}"
    padding: "0 14px"
    height: "32px"
  button-icon-accent:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.canvas}"
    rounded: "11px"
    size: "36px"
  input-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "0 12px"
    height: "40px"
  card-project:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "16px"
  composer-prompt:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.prominent}"
    padding: "16px 14px 12px 18px"
  sidebar-item:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
    padding: "0 11px"
    height: "40px"
  sidebar-item-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.md}"
  modal:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.prominent}"
    padding: "28px 28px 24px"
---

# Design System: App-Spark

## Overview

**Creative North Star: "连续交付工作台"**

App-Spark 是蓝鲸内部的连续工作台：用户从首页描述需求，进入项目后持续对话，并在同一视觉系统中观察真实运行预览。界面保持冷静、任务导向和高信息可信度；深色品牌顶栏提供稳定锚点，白色工作面与冷灰蓝背景建立层次，冷蓝强调只用于操作、选择和进度。

首页可以更有氛围，以柔和冷色渐变承托唯一的大型输入器；项目列表回到克制的管理密度；工作室则把装饰降到最低，让会话、状态和预览成为主角。圆角与环境阴影表达友好而正式的产品质感，不把内部工具写成营销落地页。

**Key Characteristics:**
- 深色固定顶栏、冷蓝火花品牌标记与白色任务表面。
- 首页、项目列表和工作室共享同一语义色、类型层级和交互状态。
- 首页强调发起，项目列表强调扫描，工作室强调会话与预览并行。
- 真实业务状态始终可见；未接入能力只允许作为明确标注的静态演示。
- 中文优先，密度适中，技术标识与业务名称有清楚区分。

## Colors

调色板以冷蓝为唯一主交互声部，深墨色和冷灰构成工作台骨架，绿、琥珀、红、紫只承担明确的状态或演示语义。

### Primary
- **工作台冷蓝**（`accent`）：选择、链接、焦点邻近状态、设备模式与生成进度。
- **蓝鲸行动蓝**（`bk-primary`）：创建、确认等高承诺平台动作；悬停使用配套的 `bk-primary-hover`。
- **柔蓝选区**（`accent-soft`）：激活导航、用户消息与选中项背景；不代替白色主表面。

### Secondary
- **发布紫**（`publish`）：仅用于发布演示标识及其柔和背景，不扩展为第二套主操作色。
- **运行绿**（`live`）：成功或在线语义。
- **警示琥珀**（`warning`）：需要注意但不阻断的状态。
- **危险红**（`danger`）：删除、失败和不可逆操作。

### Neutral
- **主墨色**（`ink`）：标题、正文和高优先级图标。
- **功能灰**（`muted`）：次要正文与默认控件。
- **提示灰**（`faint`）：时间、说明、占位和低优先级元数据。
- **分隔线**（`line`）：容器边界和工作区分栏。
- **白色画布**（`canvas` / `surface`）：应用画布和主要容器。
- **冷灰底色**（`subtle-bg` / `hover-bg`）：低层级分区、悬停和不可用状态。
- **顶栏深蓝黑**（`nav-bg`）：全局品牌锚点；其文本使用 `nav-text` 或白色。

### Named Rules

**The One Cold-Blue Voice Rule.** 冷蓝负责交互、选择和进度；状态色不得抢占普通主操作。

**The State Truth Rule.** 绿、琥珀、红只表达可验证的运行、警示和失败状态，紫色演示标签不能伪装成真实发布状态。

## Typography

**Display Font:** 系统无衬线栈（优先系统 UI 与中文平台字体）  
**Body Font:** 同一系统无衬线栈  
**Label/Mono Font:** Menlo / Consolas，用于项目 ID、地址和工具详情

**Character:** 字体策略务实、中文优先，通过字号、字重和留白而不是多字体制造层次。技术数据使用等宽字体，让项目名称与系统标识可快速区分。

### Hierarchy
- **Display**（`display`）：仅用于首页主标题；紧凑字距形成明确起点。
- **Headline**（`headline`）：页面标题和确认弹窗标题。
- **Title**（`title`）：面板标题、状态标题和重要区块。
- **Body**（`body`）：默认工作台内容、表单和说明。
- **Label**（`label`）：按钮、分段控件和高优先级短标签。
- **Caption**（`caption`）：时间、提示、计数和只读状态说明。
- **Mono**（`mono`）：项目 ID、预览地址、代码和工具调用详情。

### Named Rules

**The Chinese-First Rhythm Rule.** 中文正文保持自然句式与稳定行高，不用全大写制造层级；只允许短小的系统状态标识使用英文大写。

**The Technical-ID Rule.** 等宽字体只服务技术标识和代码，不用于导航、项目名称或普通正文。

## Layout

全局应用锁定为视口高度，固定顶栏占据 `nav-h`，页面内容在其下独立滚动。首页与项目列表共享可折叠侧栏：展开宽度由 `sidebar-w` 控制，收起宽度由 `sidebar-collapsed-w` 控制；状态保存在本地。工作室不显示侧栏，以最大化会话与预览空间。

### Home Surface

首页主体使用冷灰蓝多层渐变，主视觉在可用高度内垂直居中。主输入器宽度上限为 720px；最近编辑容器宽度上限为 1080px，并只展示最多三项。内容边距随视口流动，最近项目在宽屏为三列，在紧凑屏为单列。

### Projects Surface

项目列表使用 1080px 内容上限和冷灰底色。顶部标题、计数和创建动作构成短工具栏；项目按 64px 最小行高纵向排列，名称、项目 ID、更新时间和行级操作按扫描优先级布置。紧凑屏隐藏技术 ID 与时间，保留名称和主要操作。

### Studio Surface

工作室采用左右连续分栏：会话栏固定 400px、最小 280px，预览区弹性填充。两侧工具轨均使用 `rail-h`，从而保持共同基线。预览在桌面模式贴合可用画布，在手机模式收窄为不超过 390px 的有边界设备表面。

### Responsive Behavior

唯一正式断点为 760px。该断点下隐藏侧栏、压缩顶栏与内容边距；工作室从左右分栏切换为两个整视口高度的纵向面板，并用接近式滚动吸附维持“会话—预览”顺序；预览工具条移除不可用的前进/后退按钮。响应式变化优先保留真实业务动作和状态，装饰性火花可隐藏。

### Named Rules

**The Continuous Path Rule.** 首页发起、项目管理与工作室必须看起来属于同一条任务路径，而不是三个独立站点。

**The Two-Panel Studio Rule.** 宽屏同时保留会话和预览；窄屏按会话在前、预览在后的完整面板堆叠，不把任一业务面板压缩成不可用细栏。

## Elevation & Depth

系统以白色表面、冷灰分区和细边框建立主要层级，阴影只用于可交互卡片、浮层、手机预览和模态框。静止工作区保持平坦；悬停只做轻微抬升，浮层使用柔和、向下扩散的环境阴影，不使用硬边或明显偏移的装饰阴影。精确阴影词汇记录在 sidecar。

### Named Rules

**The Flat-Workspace Rule.** 顶栏、侧栏、会话栏和桌面预览依靠色面与分隔线分层，常驻阴影不得切碎工作区。

**The Earned-Elevation Rule.** 只有悬停反馈、弹出层、手机设备框和模态任务获得环境阴影，且层级越高扩散范围越大。

## Shapes

形状语言从紧凑控件到大型任务容器逐级变圆：小图标和输入控件采用小圆角，卡片与消息采用中圆角，主输入器与模态框采用最显著圆角，计数与状态徽标使用胶囊形。用户与助手消息通过单侧收紧的底角表达方向，不依赖额外头像。

品牌火花是唯一的非圆角签名几何：八向火花剪影只出现在品牌标记和首页标题附近。业务界面图标统一通过 `AppIcon` 复用正式原型的 24×24 Lucide 路径，使用 2px 描边、圆角端点与圆角连接；BKUI 自带图标只保留在原型本就采用 BKUI 路径的位置。

### Named Rules

**The Radius-by-Importance Rule.** 圆角随任务容器的重要性增大；不要给所有元素统一成同一个半径。

**The One-Spark Signature Rule.** 火花几何是品牌签名而不是通用装饰，只用于品牌锚点和首页欢迎时刻。

## Components

### Application Shell

- **Header:** 56px 深色顶栏固定承载品牌与账号；品牌链接返回首页，并提供明确键盘焦点。
- **Sidebar:** 白色导航可在 224px 与 64px 之间折叠；激活项使用柔蓝底与冷蓝文本，紧凑屏完全隐藏。
- **Rails:** 工作室两侧工具轨共享 56px 高度与底部分隔线。

### Buttons

- **Primary:** 蓝鲸行动蓝用于创建与确认；采用中等圆角、白字和紧凑高度。
- **Ink:** 工作室发送使用主墨色，避免在高频会话动作中滥用主蓝。
- **Icon:** 32–36px 方形点击面，默认透明或强调色；图标使用内联 SVG 或既有图标组件。
- **Disabled:** 降低文本与背景对比并移除指针暗示，但保留可读说明。
- **Focus:** 键盘焦点统一使用可见的冷蓝双像素轮廓与偏移，不仅依赖颜色变化。

### Composers & Fields

- **Home Composer:** 20px 圆角白色容器，包含可增长文本区、工具条和强调发送按钮；聚焦通过边框与柔和焦点环响应。
- **Studio Composer:** 16px 圆角、44px 最小输入高度；Enter 发送，Shift + Enter 换行，并在忙碌或只读会话中解释禁用原因。
- **Fields:** 普通字段为白底、细边框和小圆角；聚焦切换为冷蓝边框或焦点环，错误状态使用危险色并伴随文本。

### Cards, Rows & States

- **Recent Cards:** 三列或单列白卡，悬停轻微上移；名称优先，更新时间次要，危险操作隐藏在行级菜单中。
- **Project Rows:** 低高度横向扫描，项目名称、等宽 ID 和更新时间按优先级排列。
- **Empty / Loading / Error:** 空状态给出下一步，骨架与进度条表达等待，错误文本必须带重试或恢复动作。

### Conversation

- **User Message:** 柔蓝气泡靠右，右下角收紧。
- **Assistant Message:** 白色轻阴影气泡靠左，左下角收紧；Markdown、工具调用和生成进度保持在同一消息流。
- **Archive:** 归档会话明确标注只读，并提供返回当前会话动作；不让只读状态看起来仍可发送。

### Preview Workspace

- **Toolbar:** 单一“预览”分段控件、真实源码下载动作和发布演示入口。
- **Browser Bar:** 禁用的跨域前进/后退按钮保持可见并解释原因；设备切换、地址、外部打开和刷新使用真实状态。
- **Canvas:** 只有预览地址就绪时挂载 iframe；其余阶段展示准确的准备、启动、停止或不可用文案。

### Modals & Destructive Actions

- **Modal:** 白色 20px 圆角面板置于半透明深色遮罩上，标题、描述和右对齐动作保持清晰。
- **Delete:** 删除项目是真实业务操作，必须输入项目 ID 才可提交，并显示不可恢复后果、提交中和错误状态。

### Real Interactions and Static Demos

- **Real business interactions:** 项目创建、列表、进入、删除；会话发送、新建、归档查看和返回；运行预览轮询、刷新、外部打开；源码下载和账号退出均连接真实路由、状态或接口。
- **Static demos:** 项目重命名与发布/下架流程尚未接入后端。入口必须直接显示“演示”或 “DEMO”，面板必须写明“静态界面演示”以及不会调用接口或影响项目，结果不得暗示已持久化或已上线。
- **Unavailable controls:** 附件和模型切换等未支持能力保持禁用，并通过提示说明原因；不得模拟成功反馈。

### Motion & Accessibility

- 状态过渡以短促的颜色、边框、阴影和位移反馈为主；品牌火花、骨架、旋转器和预览进度只服务识别或等待。
- `prefers-reduced-motion: reduce` 下停止装饰动画、骨架、旋转器和抬升过渡；不依赖动画传达唯一状态。
- 交互元素使用原生 button、link、input 语义；图标按钮提供 `aria-label`，装饰 SVG 使用 `aria-hidden`，加载、错误和只读状态使用恰当 role 或 aria 属性。
- 键盘路径保留 `:focus-visible` 轮廓；禁用状态同时使用原生 `disabled` 或清楚的 `aria-disabled` 与说明。

### Named Rules

**The Honest-Control Rule.** 一个控件要么执行业务动作，要么被清楚禁用，要么在入口和结果两处标注为静态演示；不存在看似成功但没有后端效果的第四种状态。

**The State-in-Place Rule.** 加载、错误、只读和预览阶段在任务发生的位置反馈，不用脱离上下文的装饰替代业务状态。

## Do's and Don'ts

### Do:
- **Do** 保留深色顶栏、白色任务表面和冷蓝交互强调的三层骨架。
- **Do** 让首页、项目列表和工作室分别服务发起、扫描和持续交付，同时复用同一 token 与组件状态。
- **Do** 在所有真实异步操作中提供加载、禁用、错误与恢复路径。
- **Do** 为键盘焦点、语义状态和减少动态效果提供与鼠标体验同等完整的反馈。
- **Do** 让静态演示在入口、面板说明和结果文案中持续可辨认。

### Don't:
- **Don't** 把内部工作台改写成包含客户证言、指标或夸张营销文案的落地页。
- **Don't** 用状态色装饰普通内容，或让发布紫与主行动蓝竞争。
- **Don't** 在工作区常驻大面积阴影、硬偏移阴影或无功能的装饰面板。
- **Don't** 把窄屏工作室压成两条细栏；应堆叠完整会话与预览面板。
- **Don't** 把未接入接口的重命名、发布或下架动作呈现为真实持久化结果。
