该目录内部为配合 engine 模块本地开发以及单元测试运行设置的 Docker 配置文件，其中包括：

- etcd0：为 apiserver 提供 etcd 服务
- apiserver：Kubernetes apiserver 组件，用于单元测试

请使用 `start.sh` 脚本启动服务。此处启动的 apiserver 仅为 1.8 版本，不支持部分单元测试用例。
详细说明见项目的 README 文件。