# ChangeLog

## v2.0.0

- 新增：heroku-noble (ubuntu-24, buildpack: py-v287, go-v206)
- 移除：heroku-bionic / jammy (ubuntu-18 / 22) 构建工具
- 移除：暂未启用的 [paketo 构建工具](https://github.com/paketo-buildpacks/bionic-base-stack)
- 移除：部分 bk-buildpack-python 中的 [patch](https://github.com/TencentBlueKing/blueking-paas/pull/2143#discussion_r2092281296)

备注：
- noble 版本基础镜像支持 Python 3.11 -> 3.13，Go 1.1 -> 1.24
- 存量 bionic 版本构建工具维护在分支：[builder-stack-1.x](https://github.com/TencentBlueKing/blueking-paas/tree/builder-stack-1.x)
- 存量 bionic 版本构建工具（v1.x.x）可用于支持低版本的 Python 应用

## v1.1.0

- 新增：支持远程 buildpack

## v1.0.3

- 新增：开发沙箱 diff API
- 新增：开发沙箱支持 v3 版本的 app_desc.yaml
- 重构：Supervisor 重构 & 进程操作
- 更新：升级 bk-buildpack-go 到 v205
- 修复：launcher 没有初始化配置导致获取进程失败

## v1.0.2

- 新增：开发沙箱支持不同的源代码获取方式（http / 对象存储）
- 新增：开发沙箱支持获取进程信息，健康状态，构建、运行日志等
- 更新：升级 cnb-builder-shim，kaniko-shim Go 版本到 1.22.8
- 修复：bk-buildpack-python 无法获取 apt buildpack 环境配置信息
- 修复：修改默认 PIP_VERSION 为 22.2.2

## v1.0.1

- 新增：支持通过 `CNB_EXIT_DELAY` 环境变量来控制 builder 执行完成后的退出实现（格式：1h / 10m）

## v1.0.0

- 新增：蓝鲸云原生应用构建工具 & bk-buildpacks
