# Studio 组件（过渡 / mock）

`/studio` 是本地实验面，走 Cursor Agent + `template/`，**不接真实项目会话 API**。

和 `src/components/project/` 目录结构相近，部分文件曾经从 project 复制过来。这是有意保留的副本，不是漏抽的公共组件：

- 产品约定：Studio 保持原样，后续设计与实现不要改它。
- 真实工作台只演进 `project/`。两边现在长得像，不代表以后还要同步。
- **不要**抽到 `src/components/shared/`。抽了之后改项目顶栏会连带改 Studio。
- 删除计划：Studio 下线时整目录 + `views/studio` + `layouts/StudioLayout.vue` + `store/studio.ts` 一起删；在此之前维持复制。

占位文案和假版本数据见各文件里的 `TODO`。
