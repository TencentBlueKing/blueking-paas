# E2E test for ingress-nginx

与 ingress-nginx 交互的 E2E 测试

# 本地开发指引

进行 E2E 测试前, 需要执行以下流程进行环境初始化
1. 搭建 k8s 集群

推荐使用 [kind](https://kind.sigs.k8s.io/) 搭建本地的 k8s 集群环境。

1.1. [安装 Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)

1.2. 使用 Kind 搭建 k8s 集群

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
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        # 标记节点允许允许 ingress-nginx, 默认情况下 ingress-nginx 的 nodeSelector 需要该标签
        # kind-node=true 用于标记该节点上 kind 创建的, 避免其他测试修改或删除该节点
        node-labels: ingress-ready=true,kind-node=true
  extraPortMappings:
  # 默认情况下, ingres-nginx 默认监听容器内的 80 和 443 端口, E2E 测试需要在集群外访问 ingres-nginx, 因此需要将端口暴露到宿主机
  # 以下配置的 hostPort 仅供参考, 具体值可以自行修改
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
EOF

# 创建 1.20 版本的 k8s 集群, 更多的 k8s 发行版本信息请关注 https://github.com/kubernetes-sigs/kind/releases
❯ kind create cluster --image kindest/node:v1.20.15@sha256:6f2d011dffe182bad80b85f6c00e8ca9d86b5b8922cdf433d53575c4c5212248 --config=./kind.yaml
```

执行 `kind create cluster` 后, 将在本机启动一个运行着 k8s 集群的容器。

1.3. 验证集群状态

```bash
# 获取集群访问配置
❯ kind get kubeconfig >> config.yaml

# 查询节点状态
❯ kubectl get node --kubeconfig config.yaml
```

2. 完善本地配置
本项目使用 dynaconf 加载用户配置, 详细的配置说明请阅读 [配置文件](./paas_wl/paas_wl/settings/__init__.py)。

其中与 ingress-nginx E2E 相关的配置项如下:
```python
E2E_INGRESS_CONFIG = {
    # 运行 ingress-nginx 的宿主机 IP
    "NGINX_NODE_IP": "xxx",
    # 宿主机上暴露 nginx http 服务的端口
    "NGINX_HTTP_PORT": 8080,
    # 宿主机上暴露 nginx https 服务的端口
    "NGINX_HTTPS_PORT": 8443,
}
```

# E2E Test Suit for ingress-nginx
## ingress-nginx==0.21.0
- test rewrite-target without pattern
- X-Script-Name should return the path in ingress rule
- test Ingress Resource in extensions/v1beta1
- test Ingress Resource in networking.k8s.io/v1beta1
- k8s supported version in [1.8 ~ 1.22]
## ingress-nginx==0.22.0
- test rewrite-target with pattern
- X-Script-Name should be the sub-path provided from platform or custom domain
- test Ingress Resource in extensions/v1beta1
- test Ingress Resource in networking.k8s.io/v1beta1
- k8s supported version in [1.8 ~ 1.22]
## ingress-nginx==1.0.0
- test rewrite-target with pattern
- X-Script-Name should be the sub-path provided from platform or custom domain
- test Ingress Resource in networking.k8s.io/v1beta1
- test Ingress Resource in networking.k8s.io/v1
- k8s supported version in [1.19 ~ 1.22]
## ingress-nginx==1.4.0
- test rewrite-target with pattern
- X-Script-Name should be the sub-path provided from platform or custom domain
- test Ingress Resource in networking.k8s.io/v1
- k8s supported version in [1.22 ~ 1.25]