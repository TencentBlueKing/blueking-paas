# workloads

workloads 模块负责操作 k8s 资源。

# 本地开发指引

本地开发时依赖的一些服务，可使用 `docker-compose` 快速启动。
1. [安装 Docker](https://docs.docker.com/engine/install/)

2. [安装 Docker Compose](https://docs.docker.com/compose/install/)

3. 启动依赖

确保本地环境已安装好 `docker` 和 `docker-compose` 后, 参考以下指令即可启动并初始化 MySQL/Redis/Minio 等依赖服务。相关服务的配置，请参考 `bkpaas/workloads/dev_utils/eng_bundle/README.md`

```bash
# 假设你当前在 workloads 项目的根目录下

❯ cd dev_utils/eng_bundle
❯ ./start.sh
```

4. 搭建 k8s 集群

推荐使用 [kind](https://kind.sigs.k8s.io/) 搭建本地的 k8s 集群环境。

4.1. [安装 Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)

4.2. 使用 Kind 搭建 k8s 集群

默认情况下, kind 会自动创建最新的 k8s 集群。为了保证 bkpaas 支持搭建的 k8s 集群, 我们需要通过额外参数指定创建的集群版本和相应的配置。

```bash
# 声明集群配置, 更多配置请参考 https://kind.sigs.k8s.io/docs/user/configuration/
❯ cat > kind.yaml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  # apiServerAddress 填写 apiserver 的访问地址, 如果你的 k8s 集群搭建在本机, 填写 127.0.0.1 即可
  # 如果该值被修改, 后续配置的集群信息也需要保持一致。
  apiServerAddress: "127.0.0.1"

  # 默认情况下, kind 启动的 API Server 会监听随机端口, 建议将端口指定为 6443.
  # 如果该值被修改, 后续配置的集群信息也需要保持一致。
  apiServerPort: 6443
EOF

# 创建 1.20 版本的 k8s 集群, 更多的 k8s 发行版本信息请关注 https://github.com/kubernetes-sigs/kind/releases
❯ kind create cluster --image kindest/node:v1.20.15@sha256:6f2d011dffe182bad80b85f6c00e8ca9d86b5b8922cdf433d53575c4c5212248 --config=./kind.yaml
```

执行 `kind create cluster` 后, 将在本机启动一个运行着 k8s 集群的容器。

4.3. 验证集群状态

```bash
# 获取集群访问配置
❯ kind get kubeconfig >> config.yaml

# 查询节点状态
❯ kubectl get node --kubeconfig config.yaml
```

## 准备 Python 开发环境

1. 安装 Python 3.8

可以使用 [pyenv](https://github.com/pyenv/pyenv) 管理本地的 python 环境
- 依照 [相关指引](https://github.com/pyenv/pyenv#getting-pyenv) 安装 pyenv
- 使用 pyenv 安装 Python 3.8

```bash
❯ pyenv install 3.8.13
```

2. 安装项目依赖

本项目使用 [poetry](https://python-poetry.org/) 管理项目依赖。

- 安装 poetry
```bash
❯ pip install poetry
```

- 使用 poetry 安装依赖
```bash
# 假设你当前在 workloads 项目的根目录下

❯ poetry install --no-root
```

完成依赖安装后，便可以使用 poetry 启动项目了，常用命令：
- poetry shell：进入当前的 virtualenv
- poetry run {COMMAND}：使用 virtualenv 执行命令

## 完善本地配置

本项目使用 dynaconf 加载用户配置, 详细的配置说明请阅读 [配置文件](./paas_wl/paas_wl/settings/__init__.py)。

## 测试

启动单元测试：

```bash
# 假设你当前在 workloads 项目的根目录下

❯ cd paas_wl
❯ pytest --reuse-db -s --maxfail 1 .
```

- `--reuse-db` 表示在每次启动测试时尝试复用测试数据库
- `-s` 表示打印标准输出

### 配置测试所需的 Kubernetes apiserver

建议参考之前步骤，用 kind 在本地启动一个专用于测试的 Kubernetes 集群。你需要将该集群的相关信息放入配置文件中，部分测试用例会直接访问集群的 apiserver 服务。

1. 打开 `~/.kube/config` 查看测试集群的相关配置
2. 将其中的地址、 CA、客户端证书等信息放入 workloads 配置文件

一份有效配置如下所示：

```YAML
FOR_TESTS_APISERVER_URL: https://127.0.0.1:34567
FOR_TESTS_CA_DATA: LS0tL...
FOR_TESTS_CERT_DATA: LS0tL...
FOR_TESTS_KEY_DATA: LS0tL...
```

默认情况下，不同集群版本所执行的测试用例稍有不同：

- 集群版本 < 1.17：不执行与 BkApp CRD 相关的测试
- 集群版本 >= 1.17：执行所有测试


# 服务备忘

## 修改本地 kube config 文件

为了支持 apiserver 的故障切换功能，你需要给默认 kubectl config 配置文件添加 tag 字段：

```yaml
- context:
    cluster: docker-for-desktop-cluster
    user: docker-for-desktop
    # 追加 tag 字段
    tag: docker-for-desktop
  name: docker-for-desktop
current-context: docker-for-desktop
```

## 生成所有 Region 的状态快照

本服务可以保存所有集群在某个时间的快照，里面包含所有节点的 IP 地址等信息。该信息可以在应用需要
访问设置了 IP 白名单的外部服务时使用。

当某个 Region 的集群状态发生变更时，你需要执行 `python manage.py region_gen_stat` 命令来更新集群状态
快照。

```bash
python manage.py region_gen_state --ignore-labels 'region=szh' 'region=sz'
python manage.py region_gen_state --region default --ignore-labels 'region=szt' 'region=sz'
# 过滤集群
python manage.py region_gen_state --region default --cluster-name=default-cluster
```
