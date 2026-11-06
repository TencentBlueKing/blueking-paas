# App-Spark Agent Runtime

沙箱内的编码 Agent。一个进程绑定一个会话和一个 workspace，通过 AG-UI over HTTP/SSE 接收新消息，
把会话状态存在 workspace 之外，并复制到控制面和 Project 的 Git 仓库，所以 Runtime 本身可以随时丢弃。

本组件与 `app-spark-api` 平级，HTTP 用 FastAPI 实现。

## 快速开始

```bash
uv sync
make test
```

本地用假模型跑起来、调用接口、构建镜像，见[开发指南](docs/dev_guide.md)。

## 文档

上手：

- [开发指南](docs/dev_guide.md)：环境准备、本地跑起来、调用 HTTP、本地镜像与 cube 约定、测试分类。
- [配置项参考](docs/ref_settings.md)：全部 `APP_SPARK_AGENT_*` 配置项及缺省值，与 `settings.py` 同步。

设计：

- [Harness 生命周期](docs/harness_lifecycle.md)：启动、一轮 run 的收尾、未保存时的下一轮、关停与空闲退出。
- [Harness 状态](docs/harness_state.md)：会话状态、复制到控制面、Git 持久化、检查点与恢复。
- [用户应用架构](docs/user_app_arch.md)：Agent 所写应用的形态、项目依赖、平台配置，以及怎么在沙箱里拉起。
- [安全](docs/security.md)：凭据保护的原则。
