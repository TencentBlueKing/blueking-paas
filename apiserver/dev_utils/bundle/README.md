该目录内部为配合 apiserver 模块本地开发以及单元测试运行设置的 Docker 配置文件，其中包括：

- bk_paas3_mysql: MySQL 组件, 用于存储业务数据
- bk_paas3_minio: 对象存储组件, 用于存储二进制对象
- bk_paas3_redis: Redis 组件, 用于数据缓存、任务队列和模块间通讯

要启动这些服务，你需要在 bundle 目录下创建 `.env` 文件，内容为：

```bash
# 存储服务数据的目录，可修改为其他路径
STORAGE_ROOT=~/paasng_services

# 服务安全配置，建议修改为其他值
MYSQL_ROOT_PASSWORD=your_mysql_password
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=your_minio_secret
REDIS_PASSWORD=your_redis_password
```

待服务成功启动后，便可用对应的端口号和密码访问。