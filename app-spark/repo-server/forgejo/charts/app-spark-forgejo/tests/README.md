# Chart 验证

## 本地模板回归

在 `repo-server/forgejo/` 目录执行，无需集群：

```bash
helm dependency build charts/app-spark-forgejo
helm lint --strict charts/app-spark-forgejo \
  -f charts/app-spark-forgejo/tests/kind-values.yaml
```

必填项和不变量的守卫可以直接用 `helm template` 断言，每条都应当报错退出：

```bash
C=charts/app-spark-forgejo; V="-f $C/tests/kind-values.yaml"
helm template t $C $V --set replicaCount=2
helm template t $C $V --set database.host=
helm template t $C $V --set auth.adminPassword=
helm template t $C $V --set ingress.host=
helm template t $C $V --set extraConfig.FORGEJO__repository__DEFAULT_PRIVATE=public
helm template t $C $V --set-string server.rootUrl=repo.example.com
helm template t $C $V --set-string 'server.rootUrl=http://[::1]:3000'
```

## kind 集群冒烟验证

这些文件只用于独立测试 namespace，密码是公开的临时测试值。不要用于生产。
需已有 kind 集群、可用的默认 StorageClass，以及 Docker、kind、kubectl、Helm。
以下命令在 `repo-server/forgejo/` 目录执行，使用本次验证的 `kind-bkms-ut` context。

### 构建与部署

```bash
docker build -t app-spark-forgejo:helm-test .
docker pull mysql:8.4.11
kind load docker-image app-spark-forgejo:helm-test mysql:8.4.11 --name bkms-ut
kubectl --context kind-bkms-ut apply -f charts/app-spark-forgejo/tests/mysql.yaml
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test rollout status deployment/mysql
helm upgrade --install app-spark-forgejo charts/app-spark-forgejo \
  --kube-context kind-bkms-ut -n app-spark-forgejo-helm-test \
  -f charts/app-spark-forgejo/tests/kind-values.yaml \
  --wait --wait-for-jobs --timeout 8m
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test get pods,jobs,pvc,ingress
```

release 名就叫 `app-spark-forgejo`，这样 fullname 与 release 同名，
[verify-job.yaml](verify-job.yaml) 里的 ConfigMap / Secret / Service 名才能写死。

MySQL 与 Forgejo 各挂一个 1Gi PVC。`kind-values.yaml` 有意把 `ingress.host` 设成集群里
解析不到的主机名：生产就是这个形状（对外地址走 Ingress，集群内调用方走 Service），
顺带验证两者不一致时 Git over HTTP 仍然可用。改镜像 tag 时构建和 load 命令要同步改。

### 验收服务端不变量

```bash
kubectl --context kind-bkms-ut apply -f charts/app-spark-forgejo/tests/verify-job.yaml
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test \
  wait --for=condition=complete --timeout=5m job/forgejo-verify
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test logs job/forgejo-verify
```

这个 Job 在独立 Pod 里跑 `app-spark-forgejo verify-remote`，通过 Service 访问服务端，
因此同时证明了集群内其他 Pod 能完成真实的 clone / push。它覆盖 `just verify` 中与部署方式
无关的那部分：真实 clone/push、强推被拒、推送不存在的仓库名失败、服务账号 Basic Auth、
新建仓库是 private 且匿名访问被拒、重复 init 不产生重复账号。剩下两条（Compose 网络可达性、
`docker compose stop/up` 后仓库仍在）是 Compose 特有的，在集群里对应下面这步。

重跑该 Job 前要先 `kubectl delete job forgejo-verify`；Job 的 pod 模板不可变更。

### 验证 Pod 重建后仓库仍在

```bash
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test \
  delete pod -l app.kubernetes.io/component=server
kubectl --context kind-bkms-ut -n app-spark-forgejo-helm-test \
  rollout status deployment/app-spark-forgejo
```

再执行一次上面的 verify Job：`phase1-verify` 仓库会被复用而不是重建，
clone 到的历史里有上一轮推的提交，说明 PVC 上的 Git 对象没丢。
重新执行 Helm upgrade 命令同样可以验证新 revision 的 init Job 幂等。

### 验证数据库不可用会阻止启动

只在上述独立测试 release 上执行：

```bash
helm upgrade app-spark-forgejo charts/app-spark-forgejo \
  --kube-context kind-bkms-ut -n app-spark-forgejo-helm-test \
  -f charts/app-spark-forgejo/tests/kind-values.yaml \
  --set-string database.password=intentionally-wrong-test-password \
  --set init.timeoutSeconds=30 --wait --wait-for-jobs --timeout 100s
```

预期命令失败：`/api/healthz` 连不上数据库，server Pod 起不来（不断重启），
init Job 等就绪超时后标记 Failed。验证后必须重新执行正常的 Helm upgrade 命令恢复 release，
再跑一次 verify Job 确认恢复。

测试资源可以保留供排查。需要清理时，先确认 namespace 中只有本次测试数据：
`kind-values.yaml` 里 `persistence.retainOnDelete=false`，所以删除
`app-spark-forgejo-helm-test` namespace 会连同两个 PVC 一起删除。
