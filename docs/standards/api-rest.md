# 接口协议规范（REST + Kubernetes CRD）

<!--
  harness-preset: 降级生成（Level 2）。预设库仅有 grpc-gateway / trpc 接口预设，
  项目未使用 Protobuf/gRPC，实际接口为 REST(DRF) + K8s CRD + paas-service 协议，
  故基于 api-generic.md 骨架结合项目实际生成。如需完善为完整规范，可编写后放入
  skills/harness-engineering/assets/standards/ 并在 index.yaml 注册 rest 预设。
-->

> 本项目存在三类接口契约：① 前端/CLI ↔ apiserver 的 **REST API（Django DRF）**；② apiserver ↔ operator 的 **声明式 CRD**；③ apiserver ↔ 增强服务的 **paas-service 协议（HTTP/REST）**。

---

## 一、REST API（DRF）

### 1.1 通用原则

- 前后端**完全分离**，仅通过 REST API 交互
- 契约先行：接口变更同步更新文档/序列化器，避免前后端不一致
- 资源命名用名词复数（`/applications/`、`/modules/`），动作用 HTTP 方法表达

### 1.2 约定

| 方面 | 规则 |
|------|------|
| 入参校验 | 经 DRF Serializer，强约束（类型/长度/枚举/白名单） |
| 出参 | 统一结构，字段 snake_case |
| 分页 | DRF 内置分页；大列表必须分页 |
| 错误 | 统一错误码 + 通用提示，堆栈仅入日志（见 security §4.3.3） |
| 鉴权 | 认证 + 权限双校验，按资源 ID 校验归属（防 IDOR） |
| 版本兼容 | 禁止删除/改义已发布字段，新增字段可选 |

---

## 二、Kubernetes CRD（apiserver ↔ operator）

- CRD 是 apiserver 与 operator 的**共享契约**（`BkApp` v1alpha2 等）
- apiserver 侧由 `paas_wl` 桥接层生成 manifest 并下发；operator watch 并调和
- **禁止绕过 CRD 直接操作集群资源**，禁止 apiserver 对 operator 的直接 RPC
- CRD 字段演进遵循 K8s 版本兼容规则，跨版本用 conversion webhook

---

## 三、paas-service 协议（增强服务）

- apiserver 通过 `paasng/accessories/servicehub` 编排增强服务（svc-bkrepo/mysql/rabbitmq/otel）
- 增强服务遵循统一 `paas-service` HTTP/REST 协议，实现即插即用
- 服务实例的凭证走安全下发，禁止明文落配置/日志

---

## 四、通用约束

| 约束 | 说明 |
|------|------|
| 传输加密 | 含敏感数据接口强制 HTTPS/TLS |
| 超时/重试 | 跨服务调用配置超时、重试、退避 |
| 幂等 | 写操作与 CRD 下发保持幂等 |
| 输入即不可信 | 所有跨边界输入按外部输入校验（见 security §二） |

---

## 五、审查清单

- [ ] REST 入参经 Serializer 校验，出参结构统一
- [ ] 接口鉴权完整（认证 + 权限 + 资源归属）
- [ ] CRD 变更双向同步（operator ↔ apiserver `paas_wl`），未破坏兼容
- [ ] 未绕过 CRD 直接操作集群
- [ ] 敏感数据传输加密，凭证不明文
