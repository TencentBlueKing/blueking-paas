# bkpaas-cli

bkpaas-cli 是蓝鲸开发者中心提供的命令行工具，支持应用基础信息查看，部署，部署结果查询等功能。

## 使用指南

### 用户登录

使用本工具需要认证用户的开发者身份，如果你未认证或认证信息已过期，则需要在 bkpaas-cli 中重新登录以更新你的认证信息。

bkpaas-cli 提供交互式的用户登录能力，需要你执行 `bkpaas-cli login` 命令以进行登录。

```shell
Now we will open your browser...
Please copy and paste the access_token from your browser.
>>> AccessToken: ******  // 从唤起的浏览器窗口中复制并粘贴你的 AccessToken
User login... success!
```

### 配置信息

bkpaas-cli 通过配置文件来存储 API 访问路径，用户认证等信息，你可以在开发者中心上获取到示例配置。

默认情况下我们会读取 `${HOME}/.blueking-paas/config.yaml` 作为 bkpaas-cli 的配置，

如果你有特殊指定的需求，可以执行以下命令，bkpaas-cli 将优先使用你指定的文件作为配置：

```shell
export BKPAAS_CLI_CONFIG='/root/.blueking-paas/config.yaml'
```

你可以通过执行命令 `bkpaas-cli config view` 来查看当前加载 & 使用的配置内容：

```shell
>>> bkpaas-cli config view
configFilePath: /root/.blueking-paas/config.yaml

paasApigwUrl: http://bkapi.example.com/api/bkpaas3
paasUrl: https://bkpaas3.example.com
checkTokenUrl: https://apigw.example.com/auth/check_token/
username: admin
accessToken: [REDACTED]
```

### 蓝鲸应用管理

bkpaas-cli 可用于蓝鲸应用的信息查询，部署，部署状态查询等场景。

// TODO

### 工具版本

你可以执行 `bkpaas-cli version` 来查看当前工具的版本信息。

```shell
>>> bkpaas-cli version
Version  : 1.0.0
GitCommit: 6469e0d074f027bb08dc5ce93002177c36f3ae8e
BuildTime: 2023-03-31T15:00:00+0800
GoVersion: go1.19.4
```

## 多系统支持

bkpaas-cli 将提供适用于 Linux，MacOS，Windows 等多种系统 / 架构的二进制可执行文件。

// TODO

## 开发指南

如果你想参与到 bkpaas-cli 的开发工作中，以下内容将对你有一定的帮助。

// TODO

## 建议反馈

感谢你使用 bkpaas-cli 命令行工具，如果你有任何需求或者改进建议，欢迎到 GitHub 给我们提 [Issue](https://github.com/TencentBlueKing/blueking-paas/issues)。
