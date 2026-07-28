# 后端开发规范（Go / kubebuilder Operator）

<!--
  harness-preset: 降级生成（Level 2）。预设库仅有 go-micro / trpc-go 后端预设，
  与本项目实际（kubebuilder / controller-runtime Operator）不符，故基于
  backend-generic.md 骨架结合项目实际生成。如需完善为完整规范，可编写后放入
  skills/harness-engineering/assets/standards/ 并在 index.yaml 注册 go-kubebuilder 预设。
-->

> 适用于 `operator`（数据面 K8s Operator）及 `bkpaas-cli`、`sandbox`（Go）。技术栈：Go + kubebuilder / controller-runtime。**非** go-micro / gRPC-Gateway / tRPC 微服务。

---

## 一、技术栈要求

| 技术 | 版本要求 | 用途 |
|------|---------|------|
| Go | ≥ 1.21 | 运行时 |
| kubebuilder / controller-runtime | 项目内置 | CRD Operator 框架 |
| golangci-lint | 项目内置（`operator/.golangci.yaml`） | 静态检查（含 revive 导出注释） |
| ginkgo / envtest | 项目内置 | 控制器测试 |
| Make | 项目内置 | 构建/检查（`make lint`、`make test`、`make fmt`） |

---

## 二、项目结构与职责边界

```
operator/
├── api/                    # CRD 定义（BkApp v1alpha1/v1alpha2、DomainGroupMapping、ProjectConfig）
│   └── v1alpha2/           # 含 conversion / defaulting / validation webhook
├── controllers/            # 顶层控制器
├── pkg/controllers/        # 核心调和逻辑（Reconcile）
└── ...
```

- **CRD schema 是 apiserver 与 operator 的共享契约**：`operator/api/v1alpha2/bkapp_types.go` 变更必须同步 apiserver `paas_wl` 侧的 CRD 生成逻辑
- Operator 只通过 **watch CRD → 调和为 K8s 资源**，禁止直接被 apiserver RPC 调用

---

## 三、接口定义规范（CRD）

- CRD 类型定义是唯一事实源，字段用 `+kubebuilder` 标记声明校验/默认值
- 版本演进：新增版本（v1alphaN）通过 conversion webhook 兼容，**禁止破坏已发布字段**
- 修改 CRD 后运行 `make manifests generate` 重新生成 CRD/DeepCopy，产物纳入版本控制

---

## 四、编码规范

### 4.1 通用原则

- **Parse, Don't Validate**：CRD/外部数据在边界解析为强类型，后续只操作解析后的类型
- 错误必须显式处理（`if err != nil`），包装上下文（`fmt.Errorf("...: %w", err)`），禁止忽略
- 调和逻辑保持**幂等**，可被重复触发而结果一致
- 导出标识符须有 doc 注释（revive 强制）

### 4.2 命名约定

| 元素 | 规则 | 示例 |
|------|------|------|
| 包 | 小写、简短 | `controllers` |
| 导出函数/类型 | PascalCase | `Reconcile`, `BkApp` |
| 私有 | camelCase | `buildDeployment` |
| 常量 | 驼峰或分组 const | `DefaultReplicas` |

---

## 五、错误处理与调和

- 调和失败返回 `ctrl.Result{Requeue: true}` 或带 error，交由 controller-runtime 重试
- 通过 Status / Condition 上报调和状态，供 apiserver 观测
- 记录结构化日志（`logr`），含 CR namespace/name

---

## 六、测试规范

```bash
cd operator
make lint          # golangci-lint
make test          # ginkgo + envtest
```

| 类型 | 说明 |
|------|------|
| 单元测试 | pkg 纯逻辑，快速隔离 |
| 控制器测试 | envtest 起 apiserver + etcd，验证调和 |
| 覆盖率 | 核心调和逻辑 ≥ 70% |

---

## 七、安全规范

- 加密算法遵循 security-bk-redlines §四（AES-256-GCM / HMAC-SHA256+，`crypto/rand`）
- 禁止 `InsecureSkipVerify: true` 跳过证书校验
- webhook / metrics 端点须鉴权或仅本地监听
- 无硬编码凭证，Secret 通过 K8s Secret 注入

---

## 八、提交前自验

```bash
cd operator && make fmt && make lint && make test
```

### 审查清单

- [ ] CRD 变更已 `make manifests generate` 并同步 apiserver 侧
- [ ] 调和逻辑幂等，错误正确 requeue
- [ ] 导出标识符有注释（revive 通过）
- [ ] 无 `InsecureSkipVerify`、无硬编码凭证
- [ ] 核心逻辑有 ginkgo / envtest 测试
