# 本地开发环境搭建

本地开发时，你需要分别为以下几个模块: webfe、apiserver、workloads、operator 创建开发环境。

在开始开发前，你需要为整个项目安装并初始化 `pre-commit`，

``` bash
# 假设你当前在 bkpaas 项目的根目录下

❯ pre-commit install
```

目前我们使用了四个工具: `isort`、`black`、`flake8`、`mypy`，它们能保证你的每一次提交都符合我们预定的开发规范。

## webfe

webfe 为基于 Vue.js 的前端项目。本地开发环境搭建请参考 [webfe 模块本地开发文档](../../webfe/package_vue/README.md)

## apiserver

apiserver 主控模块，提供 API 服务。本地开发环境搭建请参考 [apiserver 模块本地开发文档](../../apiserver/README.md)

## workloads

workloads 模块负责操作 k8s 资源。本地开发环境搭建请参考 [workloads 模块本地开发文档](../../workloads/README.md)

## operator

operator 为基于 kubebuilder 构建的 k8s operator 项目。本地开发环境搭建参考 [operator 本地开发文档](../../operator/README.md)