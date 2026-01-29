# Agent Sandbox Phase 1 规格与实施计划

> 目标：在 apiserver 内落地最小可用的 Agent Sandbox（无 API/DB），基于 K8s Pod 完成创建/销毁、命令执行、单文件读写与状态查询。

## 背景与范围

### 背景
- 需要在平台内提供“沙箱”能力，为后续 Agent 功能提供基础运行环境。
- 先完成“最小闭环”，确保可演示与可验证，降低首期复杂度。

### 范围（Phase 1）
- **仅服务层**：不新增 REST API、不新增数据库模型。
- **K8s Pod 沙箱**：以 Pod 为唯一沙箱载体。
- **操作集**：create / destroy / exec / put / get / status。
- **文件操作**：仅支持单文件读写（upload/download）。
- **app 归属**：通过 `get_client_by_app(app)` 获取集群 client，并使用 `WlApp.namespace`。

### 非范围
- 鉴权、配额、回收策略、网络隔离。
- 多容器、多文件/目录、权限保留、断点续传。
- Daytona API 兼容实现（仅做语义映射预留）。

## 关键设计

### 核心抽象
- `SandboxSpec`：描述沙箱运行参数（镜像、资源、工作目录、超时）。
- `Sandbox` 接口：统一沙箱操作。
- `KubernetesPodSandbox`：使用 K8s Pod 实现 `Sandbox`。

### 默认配置
- 镜像：`busybox:latest`（hardcode）。
- 工作目录：`/workspace`（emptyDir）。
- 资源：
  - requests: CPU `0.1`, memory `512Mi`
  - limits: CPU `2`, memory `1Gi`

### Pod 模板
- `command`: `["/bin/sh", "-c", "sleep 36000"]`
- `restartPolicy`: `Never`
- `terminationGracePeriodSeconds`: `0`
- `volumeMounts`: `emptyDir` 挂载到 `/workspace`

## 接口设计（服务层）

> 仅内部调用，不暴露 API。

### Sandbox 接口
- `create() -> SandboxRef`
- `destroy() -> None`
- `exec(cmd: list[str] | str, timeout: int) -> ExecResult`
- `put(local_path: str, remote_path: str, timeout: int) -> None`
- `get(remote_path: str, local_path: str, timeout: int) -> None`
- `status() -> SandboxStatus`

### 数据结构
- `SandboxRef`：`name`, `namespace`, `app_id`
- `ExecResult`：`stdout`, `stderr`, `exit_code`
- `SandboxStatus`：
  - `phase`: Pod phase
  - `conditions`: 主要 condition（ready、reason/message）

### 错误与超时
统一异常层次：`SandboxError` 派生
- `SandboxCreateTimeout`
- `SandboxExecTimeout`
- `SandboxTransferTimeout`
- `SandboxK8sError`（封装原始 ApiException）

## K8s 实现细节

### Create
- 通过 `KPod(client).create(...)` 创建 Pod。
- `KPod.wait_for_status(... target=["Running"])`，超时即 `SandboxCreateTimeout`。

### Destroy
- `KPod.delete(...)`，容错 404。

### Exec
- `CoreV1Api(client).connect_get_namespaced_pod_exec(...)`
- `stream` 传输，返回 stdout/stderr。
- 退出码：通过 `sh -c '<cmd>; echo $? 1>&2'` 方式回传并解析。

### Put / Get（单文件）
- **put**：`tar -cf - <file>` → exec 到容器 `tar -xf - -C /workspace`
- **get**：exec `tar -cf - -C /workspace <file>` → stdout 写本地文件

## Daytona API 语义映射（预留）
- create/delete → sandbox lifecycle
- exec → command execution
- upload/download → file put/get
- status → sandbox metadata/status

## 实施步骤（落地计划）

1) **文档落地**
   - 本文档作为 Phase 1 规格说明。

2) **新增模块结构**
   - `paasng/paasng/misc/agent_sandbox/`
     - `spec.py`：SandboxSpec
     - `interfaces.py`：Sandbox 抽象
     - `kube.py`：KubernetesPodSandbox
     - `errors.py`：异常定义
     - `utils.py`：exec/tar 辅助函数

3) **核心实现**
   - 使用 `get_client_by_app` 获取 client。
   - Pod 模板构造与创建/等待逻辑。
   - exec/put/get/destroy/status 实现。

4) **演示入口**
   - 在 `dev_utils/` 加简单脚本或 management command：
     - create → exec → put → get → destroy

5) **单元测试**
   - Mock K8s client + exec stream。
   - 覆盖 create/exec/put/get/timeout/异常分支。
   - 测试文件建议：`paasng/tests/paasng/misc/agent_sandbox/test_sandbox.py`

6) **格式化**
   - `ruff format` 仅针对新增 Python 文件。

## 风险与后续
- 风险：exec 退出码解析与 stream 行为依赖 K8s client 版本。
- 后续阶段：引入 API/DB、完善鉴权/回收/资源隔离、对齐 Daytona API。
