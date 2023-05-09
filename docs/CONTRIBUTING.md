# Contributing to blueking-paas

蓝鲸团队秉持开放的态度，欢迎志同道合的开发者一起贡献项目。在开始之前，请认真阅读以下指引。

## 代码协议

[MIT LICENSE](../LICENSE.txt) 为 blueking-paas 的开源协议，任何人贡献的代码都会受此协议保护，贡献代码前请确认是否接受该协议。

## 贡献功能与特性

如果想为 blueking-paas 项目贡献功能与特性，请参考以下步骤：

- 检查已有的 [Issues](https://github.com/TencentBlueKing/blueking-paas/issues) 中是否有与需要的功能 **相关或近似** 的，若存在则请在该 issue 中进行讨论
- 若不存在相关的 issue，您可以创建新的 issue 来描述你的功能需求，蓝鲸团队会定期检查并参与讨论
- 若团队认同该功能，则需要您在 issue 中进一步补充相关设计、实现细节、测试用例等信息
- 在遵守 [蓝鲸开发规范](https://bk.tencent.com/docs/document/7.0/250/46218) 的前提下，完成功能编码，补充相应的单元测试及文档
- 如果是首次向蓝鲸项目提交代码，您还需要签署 [腾讯贡献者许可协议](https://bk-cla.bktencent.com/TencentBlueKing/blueking-paas)
- 提交 [Pull Request](https://github.com/TencentBlueKing/blueking-paas/pulls) 到 main 分支并关联对应的 issue，PR 中应包含代码、文档及单元测试
- 蓝鲸团队将及时对 PR 内容进行 Review，在通过后合并到 main 分支中

> 注意：为保证代码质量，对于大的特性与功能，在不影响现有服务功能的前提下，蓝鲸团队推荐尽可能拆分需求，分多次提交 PR 进行 Review，此种做法有利于缩短 Review 时间。

## 如何开始

想要贡献代码，建议请先参考以下文档搭建你的本地开发环境

- [本地开发部署指引](DEVELOP_GUIDE.md)

## GIT Commit 规范

蓝鲸团队推荐以 **简短且准确** 的 commit 信息来描述你修改的内容，格式参考如下：

```
git commit -m '标记: 提交的概要注释'
```

示例:

```shell
git commit -m 'fix: 修复部署状态页面进程创建时间展示异常问题'
```

### 标记说明

| 标记       | 说明            |
|----------|---------------|
| feat     | 新功能/特性开发      |
| fix      | 修复存在的 bug     |
| docs     | 添加/修改文档类内容    |
| style    | 修改注释，按代码规范格式化等 |
| refactor | 代码重构，架构调整     |
| perf     | 优化配置、参数、逻辑或功能 |
| test     | 添加/修改单元测试用例   |
| chore	| 调整构建脚本、任务等    |

## Pull Request

如果你已经在处理某个 issue，对此已经有合理的解决方案，建议你在该 issue 上进行回复，让蓝鲸团队或其他开发者、使用者了解到你对该问题有兴趣，且取得了积极的进展，防止重复开发建设，避免人力浪费。

我们欢迎大家贡献代码来共建蓝鲸 PaaS，也非常乐意与大家磋商解决方案，期待大家提交 PR。

建议提交修复的步骤：

* fork `main` 分支到你的子仓库
* 创建你自己的修复分支（如：`fix_proc_time_display`）
* 修复代码中的问题，并调整相关文档、注释等
* 调整测试用例，尽可能覆盖各种场景；如果是 bugfix，请确保在没有修复代码的情况下，无法通过该测试用例
* 在本地完成服务功能测试，并且通过所有单元测试
* 提交 PR 等待蓝鲸团队成员 Review 与合并

对于 issue 的修复，蓝鲸团队希望单个 PR 能涵盖所有相关的内容，包括但不限于代码，修复文档与使用说明。

> 注：请确保 PR title 遵循 Git Commit 规范，在开发过程中请控制单个 PR 中的 commit 数量，避免无效的反复提交。

## Issues

蓝鲸团队使用 [Issues](https://github.com/TencentBlueKing/blueking-paas/issues) 进行 bug、特性追踪。

当提交相关的 bug 时，请查找已存在或者相似的 issue 以保证不存在重复的情况。

如果确认是一个新的 bug，提交 issue 时请包含以下的信息：

* 你所使用的操作系统、开发语言版本等信息
* 当前你使用的版本信息，例如 version，commit id
* 出现问题时，相关模块的日志输出（注意不要包含敏感信息）
* 重现该问题的准确步骤，如：提交重现脚本/工具会比大量描述更加有用
