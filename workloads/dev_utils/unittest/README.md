# 单元测试执行说明

> 适用于非本地开发环境（如 CI 环境等），本地开发请使用 `eng_bundle`。

## 使用 1.8 版本的 apiserver

1. 准备工作

对于部分不支持自动创建 network 机器环境, 需要在启动 docker-compose 前手动创建 network, 执行以下指令：

```bash
docker network create ${NETWORK_NAME:-engine-unittest} --subnet="172.167.1.0/16" || echo "Done"
```

在 unittest 目录下创建 `.env` 文件，内容为：

```bash
# 存储服务数据的目录，可修改为其他路径
STORAGE_ROOT=~/workloads_services

# 服务安全配置，建议修改为其他值
MYSQL_ROOT_PASSWORD=root
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=minio_secret
```

完成依赖服务的密码配置。

2. 启动基础依赖（含 1.8 版本的 apiserver）

```bash
docker-compose -f docker-compose.yaml -p engineng up -d --remove-orphan --force-recreate
```

3. 执行测试

```bash
docker run --name "${CONTAINER_NAME:-engine-unittest}" --network ${NETWORK_NAME:-engine-unittest} \
    -e UNITTEST_CLUSTER_APISERVER_URL=${UNITTEST_CLUSTER_APISERVER_URL} \
    -e DJANGO_SETTINGS_MODULE=your_settings_module \
    your_image:${revision} \
    /bin/bash -c 'cd paas_wl && python -m pytest --maxfail 10 --init-s3-bucket tests/'
```

注意：

- 将 `your_settings_module` 替换为你的配置模块
- 将 `your_image` 替换为已使用 Dockerfile 打包好的镜像名

4. 获取单测结果

```bash
UNITTEST_OUTPUT=$(docker logs "${CONTAINER_NAME:-engine-unittest}" |tail -n 1)
echo $UNITTEST_OUTPUT
```

5. 停止依赖并删除 network

```bash
docker-compose -f docker-compose.yaml -p engineng down
docker network rm ${NETWORK_NAME:-engine-unittest} || echo "Done"
```

## 测试 1.8 版本以上的 apiserver

将 docker-compose 的 `-f` 参数调整为 `docker-compose.without-apiserver.yaml` 即可。
此时测试需依赖 kind 启动的 Kubernetes 集群。 
