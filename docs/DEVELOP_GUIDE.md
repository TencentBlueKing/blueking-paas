# 本地开发环境搭建

本地开发时，你可以根据需要，为实际开发的模块（webfe / apiserver / operator / bkpaas-cli）准备开发环境。

在开始开发前，你需要为整个项目安装并初始化 `pre-commit`，

``` bash
# 假设你当前在 blueking-paas 项目的根目录下
❯ pre-commit install
```

目前我们使用了五个工具: `ruff`、`import-linter`、`mypy`, `golangci-lint`，它们能保证你的每一次提交都符合我们的开发规范。

## webfe

`webfe` 为基于 Vue.js 的前端项目，本地开发环境搭建请参考 [本地开发文档](../webfe/README.md)

## apiserver

`apiserver` 主控模块，提供 API 服务，本地开发环境搭建请参考 [本地开发文档](../apiserver/README.md)

## operator

`operator` 是基于 [kubebuilder](https://github.com/kubernetes-sigs/kubebuilder) 构建的 k8s operator 项目，本地开发环境搭建参考 [本地开发文档](../operator/README.md)

## bkpaas-cli

`bkpaas-cli` 是基于 [cobra](https://github.com/spf13/cobra) 实现的 PaaS3.0 命令行工具，本地开发环境搭建参考 [本地开发文档](../bkpaas-cli/README.md)
