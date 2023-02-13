![img](docs/resource/img/bk_paas_zh.png)

---

[![license](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat)](https://github.com/TencentBlueKing/bk-paas/blob/main/LICENSE.txt) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/TencentBlueKing/bk-paas/pulls) [![](https://travis-ci.com/Tencent/bk-PaaS.svg?token=ypkHQqxUR3Y3ctuD7qFS&branch=master)](https://travis-ci.com/Tencent/bk-PaaS)

简体中文 | [English](readme_en.md)

> 重要提示: main 分支在开发过程中可能处于不可用状态。 请通过 [releases](https://github.com/TencentBlueKing/blueking-paas/releases) 而非 main 分支去获取稳定的版本代码。

蓝鲸智云 PaaS 平台是一个开放式的开发平台，让开发者可以方便快捷地创建、开发、部署和管理 SaaS 应用。它提供的核心服务有：PaaS 平台 - [开发者中心](https://github.com/tencentblueking/blueking-paas)、PaaS 平台 - API 网关、PaaS 平台 - [统一登录](https://github.com/TencentBlueKing/bk-user)、PaaS 平台 - [桌面](https://github.com/TencentBlueKing/blueking-console)、PaaS 平台低代码开发服务 - [可视化开发平台](https://github.com/TencentBlueKing/bk-lesscode) 等，旨在帮助用户快速、低成本的构建免运维运营系统与支撑工具。

本项目是 `PaaS平台 - 开发者中心`。

**PaaS服务核心服务开源项目**

- PaaS 平台 - [开发者中心](https://github.com/tencentblueking/blueking-paas)
- PaaS 平台 - [统一登录](https://github.com/TencentBlueKing/bk-user)
- PaaS 平台 - [桌面](https://github.com/TencentBlueKing/blueking-console)
- PaaS 平台低代码开发服务 - [可视化开发平台](https://github.com/TencentBlueKing/bk-lesscode)

## 总览

- [架构设计](docs/overview/architecture.md)
- [代码目录](docs/overview/project_codes.md)

## 功能

蓝鲸开发者中心推出全新版本，包含以下特性：

- 全新设计的用户界面，给您更友好的体验
- 前后端分离的开发模式，让 SaaS 的研发协作更高效
- 支持自定义后台进程及启动命令，更灵活的开发者视角
- 提供 MySQL、RabbitMQ、对象存储（[bk-repo](https://github.com/TencentBlueKing/bk-repo)） 等增强服务
- 通过容器镜像部署，开发蓝鲸 SaaS 变得更简单
- 全面升级 Python 开发框架，紧跟 Django 官方最新技术方案
- 新增 Node.js 开发框架，即刻享受蓝鲸可视化平台的低代码研发模式

## 快速开始

- [本地开发部署指引](/docs/install/develop_guide.md)

## 支持

- [FAQ](https://bk.tencent.com/docs/markdown/PaaS平台/产品白皮书/常见问题/FAQ.md)
- [白皮书](https://bk.tencent.com/docs/markdown/PaaS平台/产品白皮书/产品简介/README.md)
- [蓝鲸论坛](https://bk.tencent.com/s-mart/community)
- [蓝鲸 DevOps 在线视频教程](https://bk.tencent.com/s-mart/video)
- 联系我们，技术交流QQ群：

<img src="docs/resource/img/bk_qq_group.png" width="250" hegiht="250" align=center />

## 蓝鲸社区

- [BK-CI](https://github.com/Tencent/bk-ci)：蓝鲸持续集成平台是一个开源的持续集成和持续交付系统，可以轻松将你的研发流程呈现到你面前。
- [BK-BCS](https://github.com/Tencent/bk-bcs)：蓝鲸容器管理平台是以容器技术为基础，为微服务业务提供编排管理的基础服务平台。
- [BK-SOPS](https://github.com/Tencent/bk-sops)：标准运维（SOPS）是通过可视化的图形界面进行任务流程编排和执行的系统，是蓝鲸体系中一款轻量级的调度编排类 SaaS 产品。
- [BK-CMDB](https://github.com/Tencent/bk-cmdb)：蓝鲸配置平台是一个面向资产及应用的企业级配置管理平台。
- [BK-JOB](https://github.com/Tencent/bk-job)：蓝鲸作业平台（Job）是一套运维脚本管理系统，具备海量任务并发处理能力。

## 贡献

如果你有好的意见或建议，欢迎给我们提 Issues 或 PullRequests，为蓝鲸开源社区贡献力量。关于分支 / Issue 及 PR, 请查看 [CONTRIBUTING](docs/CONTRIBUTING.md)

[腾讯开源激励计划](https://opensource.tencent.com/contribution) 鼓励开发者的参与和贡献，期待你的加入。

## 协议

基于 MIT 协议，详细请参考 [LICENSE](LICENSE.txt)
