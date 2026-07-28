# 后端开发规范（Python / Django）

<!--
  harness-preset: 降级生成（Level 2）。预设库无 Python/Django 后端预设，
  基于 backend-generic.md 骨架结合本项目实际（apiserver + svc-*）生成。
  如需完善为完整规范，可编写后放入 skills/harness-engineering/assets/standards/
  并在 index.yaml 注册 python-django 预设。
-->

> 适用于 `apiserver/paasng`（控制面核心）及 `svc-bkrepo/svc-mysql/svc-rabbitmq/svc-otel` 增强服务。技术栈：Python 3.11 + Django + DRF + Celery。分层依赖由 `apiserver/paasng/.importlinter` 强制，详见 [architectural-constraints.md](../harness/architectural-constraints.md)。

---

## 一、技术栈要求

| 技术 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.11（`py311`） | 运行时 |
| Django + DRF | 项目内置 | Web 框架 + REST API |
| Celery | 项目内置 | 异步任务 |
| ruff | 项目内置 | Lint + 格式化（line-length 119） |
| mypy | 项目内置 | 静态类型检查 |
| import-linter | 项目内置 | 分层依赖契约强制 |
| pytest | 项目内置 | 测试（`pytest --reuse-db`） |

---

## 二、分层架构（强制）

依赖只能向下流动，由 `.importlinter` 契约强制（违反将阻断 pre-commit / CI）：

```
paasng.plat_admin → bk_plugins → platform → accessories → infras → core
```

- `paasng.platform.engine` 子分层：`deploy|streaming → workflow|processes → phases_steps → utils → configurations → models`
- `paas_wl`（K8s 桥接层）：`apis → bk_app → workloads → core → infras → utils`
- **新代码不得扩大 `.importlinter` 的 `ignore_imports` 豁免**（属待偿还技术债）

详细层次定义见 [architectural-constraints.md §1.2–1.4](../harness/architectural-constraints.md)。

---

## 三、编码规范

### 3.1 通用原则

- **API 层保持薄**：`views.py` / `serializers.py` 只做参数解析、校验、响应组装；业务逻辑放 domain/service 层
- **Parse, Don't Validate**：外部输入经 DRF Serializer 校验后转为强类型数据再进入业务
- 函数职责单一，显式处理异常，不吞异常
- 依赖注入优于全局单例，便于测试

### 3.2 命名约定

| 元素 | 规则 | 示例 |
|------|------|------|
| 模块/包 | 小写下划线 | `dev_sandbox` |
| 函数/变量 | snake_case | `get_application` |
| 类 | PascalCase | `ApplicationViewSet` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |

---

## 四、DRF 接口规范

- ViewSet + Serializer 组织接口，路由集中注册
- Serializer 负责入参校验与出参序列化，禁止在 view 中裸取 `request.data`
- 分页、过滤、排序使用 DRF 内置机制；动态字段名走白名单
- 接口鉴权见 [security-bk-redlines §三](security-bk-redlines.md)（认证 + 权限双校验，防 IDOR）

---

## 五、异步任务（Celery）

| 适用场景 | 说明 |
|---------|------|
| 耗时操作 | 部署、构建、日志拉取等 |
| 需重试 | 配置 `max_retries` + 退避 |
| 幂等 | 任务设计为可安全重入 |

- 任务参数视为外部输入，需校验
- 任务内异常记录日志并合理重试，避免静默失败

---

## 六、配置管理

- 配置集中在 `paasng/settings/`，环境变量优先覆盖
- 敏感信息（密码/Token/AKSK）通过环境变量或密钥系统注入，**禁止硬编码**（见 security §四）
- 缺失必填配置启动即失败（fail-fast）

---

## 七、日志规范

- 结构化日志，禁止拼接；敏感字段脱敏（Authorization/Cookie/Token → `***`）
- `DEBUG` 不进生产；`INFO` 及以上禁止含原始敏感值
- 关键链路含 request_id / 应用标识 / 耗时

---

## 八、测试规范

```bash
cd apiserver/paasng
pytest --reuse-db          # 复用测试数据库
```

| 层 | 覆盖建议 |
|----|---------|
| service / domain | ≥ 80% |
| utils | ≥ 90% |
| API（views） | 关键路径覆盖 |

- 外部依赖（K8s、增强服务、IAM）使用 mock / fixture
- 测试须能在代码破坏时失败，避免误报

---

## 九、提交前自验

```bash
pre-commit run -a          # ruff / mypy / import-linter 等
cd apiserver/paasng && pytest --reuse-db
```

### 审查清单

- [ ] 未违反 import-linter 分层契约，未扩大豁免
- [ ] API 层薄，业务在 service/domain 层
- [ ] 外部输入经 Serializer 校验（Parse, Don't Validate）
- [ ] 无硬编码凭证，日志已脱敏
- [ ] 敏感接口认证 + 权限双校验
- [ ] 新增/变更逻辑有测试
