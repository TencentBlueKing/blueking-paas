# AI Agent 多容器支持 - 实现方案与变更范围

## 一、方案选型建议

### Sidecar 镜像来源：推荐方案 B（独立构建接口）

| 维度 | 方案 A（复用蓝鲸插件构建流程） | 方案 B（独立构建接口） |
|------|------|------|
| 实现复杂度 | 高：需适配蓝盾 Pipeline 流程，涉及 `PluginRelease`/`PipelineStage` 等模块 | 低：新增一组 CRUD API + 构建任务 |
| 耦合度 | 与蓝盾 DevOps 流水线强耦合 | 仅依赖已有的应用引擎构建能力 |
| 灵活性 | 用户需通过蓝盾提交源码 | 调用方可直接指定已有镜像或触发构建 |
| 可复用性 | 后续蓝鲸插件如有类似需求可复用 | 不易复用到蓝鲸插件场景 |
| 交付周期 | 长（需协调蓝盾侧） | 短 |

**推荐理由**：
1. 当前 AI 平台团队的核心诉求是"能指定 sidecar 镜像"，而非"需要完整的源码构建流水线"
2. 方案 B 的最小实现可简化为"注册已有镜像" + "创建应用时引用"，MVP 阶段无需构建能力
3. 后续如需构建能力，可基于现有 `ApplicationBuilder` 扩展，无需引入蓝盾依赖

### 方案 B 的分阶段策略

- **Phase 1（本期）**：仅支持"注册已有镜像" —— 调用方先自行构建好镜像推到仓库，通过 API 注册镜像信息到平台
- **Phase 2（后续按需）**：平台提供 sidecar 源码构建能力，复用 `BuildProcess` + `ApplicationBuilder` 链路

---

## 二、整体架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│                                                                 │
│  [新] POST /api/bkapps/ai_agent/sidecar_images/                 │  ← 注册 sidecar 镜像
│  [改] POST /api/bkapps/applications/ai_agent/                   │  ← 创建应用时传入 sidecars
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                       Model Layer                                │
│                                                                 │
│  [新] SidecarImage (model)       — 存储已注册的 sidecar 镜像信息  │
│  [新] AppSidecarConfig (model)   — 存储应用绑定的 sidecar 配置    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      Deploy Layer                                │
│                                                                 │
│  [改] build_sandbox_spec_from_deploy()  ← 从 DB 读取 sidecar 配置│
│  [改] SandboxInstanceSpec               ← 新增 sidecars 字段     │
│  [改] build_manifest()                  ← 渲染多容器 podTemplate  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    K8s CR Layer                                   │
│                                                                 │
│  SandboxInstance CR                                              │
│    spec.podTemplate.containers: [main, sidecar-1, sidecar-2]    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、详细变更清单

### 3.1 新增文件

| 文件路径 | 用途 |
|---------|------|
| `apiserver/paasng/paasng/platform/ai_agent/models.py` | SidecarImage、AppSidecarConfig 模型定义 |
| `apiserver/paasng/paasng/platform/ai_agent/serializers.py` | API 序列化器 |
| `apiserver/paasng/paasng/platform/ai_agent/views.py` | sidecar 镜像注册/查询 API |
| `apiserver/paasng/paasng/platform/ai_agent/urls.py` | URL 路由 |
| `apiserver/paasng/paasng/platform/ai_agent/migrations/0001_initial.py` | 数据库迁移 |

### 3.2 修改文件

| 文件路径 | 变更内容 | 变更级别 |
|---------|---------|---------|
| `paas_wl/bk_app/sandbox_instance/entities.py` | 新增 `SidecarContainer` 数据类；`SandboxInstanceSpec` 新增 `sidecars` 字段；`build_manifest()` 支持多容器渲染 | 核心 |
| `paasng/platform/engine/deploy/release/sandbox_operator.py` | `build_sandbox_spec_from_deploy()` 读取 DB 中的 sidecar 配置并传入 spec | 核心 |
| `paasng/platform/applications/serializers/creation.py` | `AIAgentAppCreateInputSLZ` 新增 `sidecars` 参数 | 接口 |
| `paasng/platform/applications/views/creation.py` | `create_ai_agent_app` 处理 sidecar 配置存储 | 接口 |
| `paas_wl/bk_app/sandbox_instance/constants.py` | 新增 sidecar 相关常量（如最大数量限制） | 辅助 |

### 3.3 不需要修改的文件

| 文件 | 原因 |
|------|------|
| `operator.py`（部署分叉逻辑） | 分叉条件不变，仍是 `is_ai_agent_app + ISOLATED` |
| `wait_sandbox.py`（状态轮询） | 轮询的是 SandboxInstance 整体 phase，多容器不影响 |
| `resource.py`（SandboxInstanceManager） | 仅负责 CR 的 CRUD，manifest 结构变化不影响 |
| `crd.py` | CRD 定义不含 spec 细节 |

---

## 四、数据模型设计

### 4.1 SidecarImage（镜像注册表）

```python
class SidecarImage(TimestampedModel):
    """已注册的 Sidecar 容器镜像"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=64, help_text="镜像标识名，如 openclav")
    image = models.TextField(help_text="完整镜像地址，如 registry.example.com/ai/openclav:v1.0")
    description = models.TextField(blank=True, default="")
    # 限制访问范围（未来可扩展为多租户）
    tenant_id = tenant_id_field_factory()
    creator = BkUserField()
    
    class Meta:
        unique_together = ("tenant_id", "name")
```

### 4.2 AppSidecarConfig（应用 Sidecar 绑定）

```python
class AppSidecarConfig(TimestampedModel):
    """应用绑定的 Sidecar 容器配置"""
    
    application = models.ForeignKey("applications.Application", on_delete=models.CASCADE)
    module = models.ForeignKey("modules.Module", on_delete=models.CASCADE)
    # sidecar 配置（JSON 数组，每项包含 name/image/resources/ports/env_vars 等）
    sidecars = models.JSONField(default=list, help_text="sidecar 容器配置列表")
    
    class Meta:
        unique_together = ("application", "module")
```

`sidecars` JSON 结构示例：
```json
[
    {
        "name": "openclav",
        "image": "registry.example.com/ai/openclav:v1.0",
        "cpu": "2000m",
        "memory": "2Gi",
        "command": [],
        "args": [],
        "env_vars": [{"name": "PORT", "value": "8080"}],
        "ports": [{"containerPort": 8080, "protocol": "TCP"}]
    }
]
```

---

## 五、核心代码变更设计

### 5.1 SidecarContainer 数据类

```python
# paas_wl/bk_app/sandbox_instance/entities.py

@dataclass(frozen=True)
class SidecarContainer:
    """Sidecar 容器配置"""
    name: str
    image: str
    cpu: str = "1000m"         # K8s cpu quantity, 如 "1000m"
    memory: str = "512Mi"       # K8s memory quantity
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    env_vars: List[Dict[str, str]] = field(default_factory=list)
    ports: List[Dict[str, Any]] = field(default_factory=list)
    image_pull_policy: str = "IfNotPresent"
```

### 5.2 SandboxInstanceSpec 扩展

```python
@dataclass
class SandboxInstanceSpec:
    # ... 现有字段不变 ...
    
    # 新增：sidecar 容器列表（可选，为空时等同于当前单容器行为）
    sidecars: List[SidecarContainer] = field(default_factory=list)
```

### 5.3 build_manifest() 变更

```python
def build_manifest(self) -> Dict[str, Any]:
    # ... 现有逻辑不变 ...
    
    # 容器列表：主容器 + sidecar 容器
    containers = [self._build_main_container()]
    for sidecar in self.sidecars:
        containers.append(self._build_sidecar_container(sidecar))
    
    pod_template: Dict[str, Any] = {"containers": containers}
    # ... 后续逻辑不变 ...

def _build_sidecar_container(self, sidecar: SidecarContainer) -> Dict[str, Any]:
    """构建 sidecar 容器的 manifest"""
    container: Dict[str, Any] = {
        "name": sidecar.name,
        "image": sidecar.image,
        "imagePullPolicy": sidecar.image_pull_policy,
        "resources": {
            "limits": {"cpu": sidecar.cpu, "memory": sidecar.memory},
            "requests": {"cpu": sidecar.cpu, "memory": sidecar.memory},
        },
    }
    if sidecar.command:
        container["command"] = sidecar.command
    if sidecar.args:
        container["args"] = sidecar.args
    if sidecar.env_vars:
        container["env"] = list(sidecar.env_vars)
    if sidecar.ports:
        container["ports"] = list(sidecar.ports)
    return container
```

### 5.4 build_sandbox_spec_from_deploy() 变更

```python
def build_sandbox_spec_from_deploy(...) -> SandboxInstanceSpec:
    # ... 现有逻辑不变 ...
    
    # 新增：从 DB 读取 sidecar 配置
    sidecars = _resolve_sidecars_for_sandbox(env)
    
    return SandboxInstanceSpec(
        # ... 现有参数不变 ...
        sidecars=sidecars,  # 新增
    )


def _resolve_sidecars_for_sandbox(env: ModuleEnvironment) -> List[SidecarContainer]:
    """从 DB 读取应用绑定的 sidecar 配置，转换为 SidecarContainer 列表"""
    from paasng.platform.ai_agent.models import AppSidecarConfig
    
    try:
        config = AppSidecarConfig.objects.get(
            application=env.application, module=env.module
        )
    except AppSidecarConfig.DoesNotExist:
        return []
    
    return [
        SidecarContainer(
            name=s["name"],
            image=s["image"],
            cpu=s.get("cpu", "1000m"),
            memory=s.get("memory", "512Mi"),
            command=s.get("command", []),
            args=s.get("args", []),
            env_vars=s.get("env_vars", []),
            ports=s.get("ports", []),
        )
        for s in config.sidecars
    ]
```

### 5.5 AIAgentAppCreateInputSLZ 扩展

```python
class SidecarConfigSLZ(serializers.Serializer):
    """单个 sidecar 容器配置"""
    name = serializers.CharField(max_length=63, help_text="容器名，需符合 DNS subdomain 规范")
    image = serializers.CharField(help_text="镜像地址")
    cpu = serializers.CharField(default="1000m", help_text="CPU 配额，如 1000m")
    memory = serializers.CharField(default="512Mi", help_text="内存配额，如 512Mi")
    command = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    args = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    env_vars = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    ports = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class AIAgentAppCreateInputSLZ(AppBasicInfoMixin):
    # ... 现有字段不变 ...
    
    # 新增：sidecar 容器配置列表（可选）
    sidecars = serializers.ListField(
        child=SidecarConfigSLZ(),
        required=False,
        default=list,
        max_length=3,
        help_text="Sidecar 容器配置列表，最多 3 个"
    )
```

---

## 六、API 设计

### 6.1 注册 Sidecar 镜像（可选，Phase 1 可不实现）

```
POST /api/bkapps/ai_agent/sidecar_images/
```

请求体：
```json
{
    "name": "openclav",
    "image": "registry.example.com/ai/openclav:v1.0",
    "description": "AI Agent 运行时 - OpenClav 框架"
}
```

### 6.2 创建 AI Agent 应用（扩展现有接口）

```
POST /api/bkapps/applications/ai_agent/
```

请求体新增 `sidecars` 字段：
```json
{
    "code": "my-ai-agent",
    "name_zh_cn": "我的AI Agent",
    "name_en": "my-ai-agent",
    "is_isolated": true,
    "sidecars": [
        {
            "name": "openclav",
            "image": "registry.example.com/ai/openclav:v1.0",
            "cpu": "2000m",
            "memory": "2Gi",
            "env_vars": [{"name": "PORT", "value": "8080"}],
            "ports": [{"containerPort": 8080, "protocol": "TCP"}]
        }
    ]
}
```

### 6.3 更新应用 Sidecar 配置

```
PUT /api/bkapps/applications/{app_code}/modules/{module_name}/ai_agent/sidecars/
```

请求体：
```json
{
    "sidecars": [
        {
            "name": "openclav",
            "image": "registry.example.com/ai/openclav:v1.1",
            "cpu": "2000m",
            "memory": "2Gi"
        }
    ]
}
```

---

## 七、生成的 CR Manifest 示例

### 单容器（向后兼容，sidecars 为空时）

与现有行为完全一致，不赘述。

### 多容器（1 主容器 + 1 sidecar）

```yaml
apiVersion: advanced.bkbcs.tencent.com/v1beta1
kind: SandboxInstance
metadata:
  name: bkapp-my-ai-agent-stag
  namespace: bkapp-my-ai-agent-stag
  labels:
    bkapp.paas.bk.tencent.com/module-name: default
    bkapp.paas.bk.tencent.com/process-type: web
spec:
  desiredState: Running
  runtimeClassName: cube
  network:
    mode: direct-cni
  domain:
    cpu:
      cores: 4
    memory: 4Gi
  podTemplate:
    containers:
      - name: main
        image: registry.example.com/ai/adapter:latest
        imagePullPolicy: IfNotPresent
        command: ["python", "-m", "adapter"]
        env:
          - name: SIDECAR_PORT
            value: "8080"
      - name: openclav
        image: registry.example.com/ai/openclav:v1.0
        imagePullPolicy: IfNotPresent
        resources:
          limits:
            cpu: "2000m"
            memory: "2Gi"
          requests:
            cpu: "2000m"
            memory: "2Gi"
        env:
          - name: PORT
            value: "8080"
        ports:
          - containerPort: 8080
            protocol: TCP
    imagePullSecrets:
      - name: bkapp-my-ai-agent-stag--dockerconfigjson
    nodeSelector:
      # ...
    tolerations:
      # ...
```

---

## 八、约束与边界

1. **仅 ISOLATED 模式**：多容器仅在 `is_ai_agent_app=True` + `deploy_policy=ISOLATED` 时生效
2. **容器数量限制**：1 主容器 + 最多 3 sidecar = 总计最多 4 容器
3. **资源配额**：`spec.domain.cpu/memory` 为主容器资源（对应 MicroVM 规格）；sidecar 容器通过 `resources.limits` 独立配置，由 sandbox-controller 调度
4. **网络模型**：同 Pod 内通过 `localhost` 通信，Service/Ingress 仍仅指向主容器端口
5. **生命周期**：sidecar 与主容器在同一 Pod 中，由 sandbox-controller 统一管理
6. **向后兼容**：`sidecars` 为空时行为与当前单容器模式完全一致

---

## 九、待确认事项

| 编号 | 问题 | 建议 |
|------|------|------|
| Q-1 | sandbox-controller 是否已支持 `podTemplate.containers` 中的多个容器？ | 需与集群侧确认，如未支持需先在 controller 侧实现 |
| Q-2 | sidecar 容器的 `resources` 字段格式是否被 sandbox-controller 识别？ | 需确认 CR 的 schema 定义 |
| Q-3 | Phase 1 是否需要 sidecar 镜像注册 API，还是直接在 `create_ai_agent_app` 中内联传入镜像地址即可？ | 建议 Phase 1 直接内联传入，简化实现 |
| Q-4 | sidecar 容器是否需要独立的健康检查 probe？ | 建议 Phase 1 不加，依赖 sandbox-controller 默认行为 |
| Q-5 | sidecar 配置变更后是否需要重新部署才生效？ | 是，配置存入 DB 后需触发重新部署 |

---

## 十、实施步骤

1. **确认 sandbox-controller 侧支持情况**（Q-1, Q-2）
2. 新增 `SidecarContainer` 数据类和 `SandboxInstanceSpec.sidecars` 字段
3. 修改 `build_manifest()` 支持多容器渲染
4. 新增 `AppSidecarConfig` 模型 + 数据库迁移
5. 扩展 `AIAgentAppCreateInputSLZ` + `create_ai_agent_app` 接口
6. 修改 `build_sandbox_spec_from_deploy()` 读取 sidecar 配置
7. 编写单元测试（Spec 构建、Manifest 渲染、API 校验）
8. 联调测试（与 sandbox-controller 协同验证多容器 Pod 启动）
