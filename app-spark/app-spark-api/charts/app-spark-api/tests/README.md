# Chart 验证

## 本地模板回归

从 app-spark-api 项目目录执行，无需集群：

```bash
helm dependency build charts/app-spark-api
helm lint --strict charts/app-spark-api
uv run pytest --reuse-db -s --maxfail=1 tests/test_helm_configmap.py tests/test_helm_common.py
```

模板测试覆盖 Ingress class、backend、TLS、资源命名和 selector 兼容性，以及镜像摘要、
仓库覆盖和拉取凭据合并。

## kind 集群冒烟验证

这些文件只用于独立测试 namespace，密码是公开的临时测试值。不要用于生产。
需已有 kind 集群、可用的默认 StorageClass，以及 Docker、kind、kubectl、Helm。
以下命令从 app-spark-api 项目目录执行，使用本次验证的 `kind-bkms-ut` context。

### 构建与部署

```bash
helm dependency build charts/app-spark-api
docker build -f Dockerfile -t app-spark-api:helm-test-external-wait ..
docker pull mysql:8.4.11
docker pull groundnuty/k8s-wait-for:v1.5.1
kind load docker-image app-spark-api:helm-test-external-wait mysql:8.4.11 groundnuty/k8s-wait-for:v1.5.1 --name bkms-ut
kubectl --context kind-bkms-ut apply -f charts/app-spark-api/tests/mysql.yaml
helm upgrade --install app-spark-api charts/app-spark-api \
  --kube-context kind-bkms-ut -n app-spark-helm-test \
  -f charts/app-spark-api/tests/kind-values.yaml \
  --wait --wait-for-jobs --timeout 6m
kubectl --context kind-bkms-ut -n app-spark-helm-test get pods,jobs,pvc
```

MySQL 与 API 各挂载一个 1Gi PVC。Chart 的迁移 Job 创建数据库表，外部等待镜像完成后启动 API。
修改 `kind-values.yaml` 的镜像 tag 时，构建和 load 命令也应同步修改。

### 验证 Service、SSE 和 local process

```bash
kubectl --context kind-bkms-ut -n app-spark-helm-test exec -i \
  deployment/app-spark-api -c app-spark-api -- \
  uv run --no-sync python - < charts/app-spark-api/tests/smoke.py
```

脚本在测试数据库中预置有效的登录 session，然后通过 `http://app-spark-api:8000`
访问真实 API，不替换服务端认证中间件。它检查匿名访问、登录态、创建会话、SSE 事件、
Agent 写入 workspace、状态回写和历史事件读取。使用 `fake:write-file` 模型，不调用外部模型。
预置 session 不覆盖外部蓝鲸登录服务的联调。

再执行一次上面的 Helm upgrade 命令和 smoke 脚本，可验证新 revision 的迁移 Job、
Pod 重建、已有会话上下文恢复，以及 PVC 中的源码仍在。脚本会延续同一个会话，
每次成功增加一个 `fake-agent-note-N.md` 文件。

### 验证迁移失败会阻止启动

只在上述独立测试 release 上执行：

```bash
helm upgrade app-spark-api charts/app-spark-api \
  --kube-context kind-bkms-ut -n app-spark-helm-test \
  -f charts/app-spark-api/tests/kind-values.yaml \
  --set-string externalDatabase.password=intentionally-wrong-test-password \
  --set migrate.timeoutSeconds=20 --wait --wait-for-jobs --timeout 70s
```

预期命令失败，迁移 Job 报数据库鉴权失败，API 停留在 init 阶段。
验证后必须重新执行正常的 Helm upgrade 命令恢复 release，再运行 smoke 脚本确认恢复。

测试资源可以保留供排查。需要清理时，先确认 namespace 中只有本次测试数据；
删除 `app-spark-helm-test` namespace 会连同两个 PVC 一起删除，默认 StorageClass
通常也会回收其数据。
