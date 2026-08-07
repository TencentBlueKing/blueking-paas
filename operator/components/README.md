# 进程组件目录

本目录存放进程组件（process component）的定义，会被打进 operator 镜像的 `/components`
路径（见 `Dockerfile`），供 `pkg/components/manager` 在 reconcile 期间读取。

每个组件按 `<组件名>/<版本>/` 组织，包含三个文件：

- `template.yaml` — 组件模板。以 Go text/template 渲染后，通过 strategic merge patch
  合并到工作负载上。`.procName` 由operator 注入，指向进程主容器名称。
- `schema.json` — 组件参数（`properties`）的 JSON Schema。
- `docs.md` — 面向用户的参数说明与示例。

## 与 apiserver 的同步关系

同一批定义在两处各存一份：

- `operator/components/` — 本目录，operator 渲染模板时读取
- `apiserver/paasng/support-files/components/` — apiserver 校验用户参数、
  并向前端提供组件列表与文档时读取

之所以重复，是因为两者是独立的部署单元、各自构建镜像，而 operator 的 docker 构建
上下文为 `operator/`，无法引用 apiserver 目录下的文件。

**新增或修改组件时，必须同步更新两处，否则会出现 apiserver 校验通过但 operator
渲染失败（或相反）的情况。**
