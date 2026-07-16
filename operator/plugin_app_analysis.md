# 插件应用（is_plugin_app）创建链路与能力体系分析

> 分析对象：蓝鲸 PaaS 平台 `apiserver/paasng`，`Application.is_plugin_app=True` 的应用。
> 所有代码引用相对 `apiserver/paasng/` 目录。

---

## 一、核心标记与定位

| 项 | 位置 | 说明 |
|---|---|---|
| `is_plugin_app` 字段 | `paasng/platform/applications/models.py:354` | BooleanField, default=False。help_text：供标准运维、ITSM 等 SaaS 使用 |
| `is_ai_agent_app` 字段 | `paasng/platform/applications/models.py:359` | AI Agent 应用标记；AI Agent 应用创建时会强制 `is_plugin_app=True` |
| `is_bk_plugin()` 判断 | `paasng/bk_plugins/bk_plugins/models.py:340` | 全链路统一入口，仅判断 `application.is_plugin_app` |
| `BkPlugin`（Pydantic 模型） | `paasng/bk_plugins/bk_plugins/models.py:199` | 应用级插件表示，`from_application()` 工厂构造，`get_profile()` 取档案 |

**结论**：插件应用不是独立的 `app_type`，而是 `type=DEFAULT` 或 `CLOUD_NATIVE` 应用上的一个布尔标记。AI Agent 应用天生就是插件应用。

---

## 二、创建链路

### 2.1 创建入口（3 个）

| 入口 | Serializer | View | 说明 |
|---|---|---|---|
| 普通应用 v2 | `serializers/creation.py:42` `ApplicationCreateInputV2SLZ`（透传 `is_plugin_app`） | `views/creation.py:85` `create_v2()` | 可选支持插件（调用方传 true） |
| 云原生应用 | `serializers/creation.py:66` `CloudNativeAppCreateInputSLZ`（透传 `is_plugin_app`） | `views/creation.py:115` `create_cloud_native()` | 可选支持插件 |
| AI Agent 应用 | `serializers/creation.py:133` `AIAgentAppCreateInputSLZ.to_internal_value()`（第 140 行**强制** `is_plugin_app=True`） | `views/creation.py:198` `create_ai_agent_app()` | 强制插件 + CLOUD_NATIVE |
| 插件中心 | — | `bk_plugins/bk_plugins/pluginscenter_views.py` `create_plugin()`（强制 `is_plugin_app=True`） | 插件中心 shim API |

### 2.2 主流程调用链

```
view.create_*()
  └─ create_application()                     paasng/platform/applications/utils.py:78
        │  第 84 行参数 is_plugin_app; 第 105 行透传到 Application.objects.create()
        └─ create_default_module()            paasng/platform/applications/utils.py:48
              │  设置 source_init_template
              └─ init_module_in_view()        paasng/platform/modules/manager.py:511
                    └─ initialize_module()    paasng/platform/modules/manager.py:543
                          ├─ ModuleInitializer.create_engine_apps()   manager.py:119
                          │     第 145 行按 application.type 定 wl_app_type
                          └─ initialize_app_model_resource()          manager.py:290
                                仅 CLOUD_NATIVE 应用处理；CUSTOM_IMAGE 才导入 spec
```

### 2.3 关键校验分支

| 校验 | 位置 | 说明 |
|---|---|---|
| 模板类型强制 PLUGIN | `paasng/platform/modules/serializers.py:295` | `is_plugin_app=True` 时 `filters["type"]=TemplateType.PLUGIN`，否则模板校验失败 |
| AppModelResource 生成时机 | `paasng/platform/modules/manager.py:290` | 仅云原生 + CUSTOM_IMAGE 在创建期生成；buildpack/模板路径在**首次部署**时才生成 |

### 2.4 AI Agent 应用两条子路径

| 路径 | 位置 | 关键点 |
|---|---|---|
| 固定模板 | `views/creation.py:208-217` | `source_origin=SourceOrigin.AI_AGENT`；模板 `bk-ai-plugin-python`；`env_cluster_names={}`（默认集群） |
| git 源码 | `views/creation.py:219-232` | `_init_ai_agent_app_via_git()` → `_init_cloud_native_app_from_source()`，透传 `is_ai_agent_app`、`deploy_policy` |

---

## 三、创建期副作用（信号驱动）

| 时机 | 信号 | Handler | 动作 |
|---|---|---|---|
| 应用创建后 | `post_create_application` | `bk_plugins/bk_plugins/handlers.py:35` `on_plugin_app_created()` | 第 42 行建 `BkPluginProfile`；第 45-47 行写入预设使用方 `pre_distributor_codes` |
| 首次部署前 | `pre_appenv_deploy` | `bk_plugins/bk_plugins/handlers.py:50` `on_pre_deployment()` | 第 58-60 行 `is_synced=False` 时 `safe_sync_apigw()` 注册网关 |

- `BkPluginProfile.get_or_create_by_application()`：`bk_plugins/bk_plugins/models.py:49`
- **网关在「首次部署期」注册，而非创建期**。

---

## 四、对外 / 治理能力体系

### 4.1 分发 / 使用方授权（distributor）—— 插件核心能力

| 能力 | 位置 | 说明 |
|---|---|---|
| `BkPluginDistributor` 模型 | `bk_plugins/bk_plugins/models.py:135` | 代表使用方（标准运维/ITSM/AIDev），字段 `code_name`、`bk_app_code` |
| `set_distributors()` | `bk_plugins/bk_plugins/apigw.py:68` | 全量更新使用方，处理新增/移除的网关授权 |
| `safe_sync_apigw()` | `bk_plugins/bk_plugins/apigw.py:38` | 建网关 + 授权预设使用方（仅未同步时） |
| `grant_distributor()` / `revoke_distributor()` | `bk_plugins/bk_plugins/apigw.py:150` / `:166` | 单个使用方授权 / 撤销 |
| 使用方发现插件 | `bk_plugins/bk_plugins/models.py:306` `BkPluginAppQuerySet.filter()` | 按 `distributor_code_name` 过滤出已授权的插件 |

### 4.2 API 网关（apigw）

| 能力 | 位置 | 说明 |
|---|---|---|
| `PluginDefaultAPIGateway` 类 | `bk_plugins/bk_plugins/apigw.py:194` | 管理插件默认网关生命周期 |
| `sync()` | `bk_plugins/bk_plugins/apigw.py:220` | 创建/更新网关，返回网关 ID |
| `set_gw_name()` | `bk_plugins/bk_plugins/apigw.py:212` | 生成网关名 `bp-{plugin_code}` |
| `grant()` / `revoke()` | `bk_plugins/bk_plugins/apigw.py:248` / `:261` | 授权 / 撤销使用方访问网关 |
| 网关名注入环境变量 | `bk_plugins/bk_plugins/models.py:180` `get_plugin_env_variables()` | 注入 `BK_PLUGIN_APIGW_NAME` 到运行环境 |

### 4.3 插件档案 profile（元信息）

| 能力 | 位置 | 说明 |
|---|---|---|
| `BkPluginProfile` 模型 | `bk_plugins/bk_plugins/models.py:66` | introduction / contact / tag / api_gw_name / api_gw_id / pre_distributor_codes |
| 与 Application 关联 | `bk_plugins/bk_plugins/models.py:69` | OneToOne，`related_name="bk_plugin_profile"` |
| `pre_distributors` 属性 | `bk_plugins/bk_plugins/models.py:112` | 预设使用方对象集合 |

### 4.4 对外 API 接口

| 分类 | 端点 | 位置 |
|---|---|---|
| 系统 API（三方/插件中心） | 插件列表 list/retrieve | `bk_plugins/bk_plugins/views.py:92` `SysBkPluginsViewset` |
| | 批量详情（含 addresses） | `bk_plugins/bk_plugins/views.py:109` `SysBkPluginsBatchViewset` |
| | 插件日志（含 trace_id） | `bk_plugins/bk_plugins/views.py:129` `SysBkPluginLogsViewset` |
| | AI 插件授权/取消授权 | `bk_plugins/bk_plugins/views.py:177` `SysBkPluginDistributorsViewSet` |
| 前端 API | 档案读取/修改 | `bk_plugins/bk_plugins/views.py:236` `BkPluginProfileViewSet` |
| | 使用方列表读取/更新 | `bk_plugins/bk_plugins/views.py:299` `DistributorRelsViewSet` |
| 插件中心 shim | 创建插件 | `bk_plugins/bk_plugins/pluginscenter_views.py` `create_plugin()` |

### 4.5 部署状态与地址解析（AI Agent 需 HTTP 地址，重点关注）

| 能力 | 位置 | 说明 |
|---|---|---|
| `get_deployed_statuses()` | `bk_plugins/bk_plugins/models.py:273` | 返回各环境 `{deployed, addresses}`，供使用方发现 |
| `env_is_deployed()` | `paasng/accessories/publish/entrance/exposer.py:34` | → `env_is_running()` |
| `env_is_running()`（Hub） | `paas_wl/core/env.py:51` | 按 `ApplicationType` 注册实现 |
| ├ DEFAULT / ENGINELESS | `paas_wl/core/env.py:62` | `_get_env_is_running`：`Release.objects.any_successful(wl_app)` |
| └ CLOUD_NATIVE（AI Agent 走此） | `paas_wl/bk_app/cnative/specs/models/app_resource.py:279` | 同判据：有过成功 Release |
| `ModuleEnvAvailableAddressHelper` | `paasng/accessories/publish/market/utils.py:69` | 计算环境可用访问地址列表 |
| `get_exposed_url()` | `paasng/accessories/publish/entrance/exposer.py:61` | 取对外 URL |

> **替换 SandboxInstance 运行时的关键**：`env_is_running` 判据是「有过成功 Release」。若 SandboxInstance 下发仍写入成功 Release 记录，则地址解析链路可原样复用；否则需为 AI Agent 场景补偿运行态判断与 Service/Ingress 地址产出。

### 4.6 环境变量注入

| 能力 | 位置 | 说明 |
|---|---|---|
| `get_plugin_env_variables()` | `bk_plugins/bk_plugins/models.py:180` | env_vars provider，为插件应用注入 `BK_PLUGIN_APIGW_NAME` |

### 4.7 其它插件专属分支（grep `is_plugin_app` 使用点）

| 能力 | 位置 | 说明 |
|---|---|---|
| 模块数限制 | `paasng/platform/applications/specs.py:60` | 插件应用不允许新增模块 |
| Logo 区分 | `paasng/platform/applications/models.py:504` | 使用 `PLUGIN_APP_DEFAULT_LOGO` |
| 发布前分类校验 | `paasng/platform/engine/workflow/protections.py:130` | 生产部署必须设置插件分类 tag |
| 模板限制 | `paasng/platform/modules/serializers.py:295` | 仅允许 `TemplateType.PLUGIN` 模板 |
| 应用列表展示 | `paasng/platform/applications/views/application.py:107` | `DISPLAY_BK_PLUGIN_APPS=False` 时过滤插件应用 |
| 平台管理后台 | `paasng/plat_mgt/applications/views/application.py:139` | 判断是否展示插件管理操作 |

---

## 五、整体流程串联

```
创建（is_plugin_app=True）
  → post_create_application 信号
  → on_plugin_app_created()：建 BkPluginProfile + 写预设使用方
  → 首次部署 pre_appenv_deploy 信号
  → on_pre_deployment()：safe_sync_apigw() 注册网关 + 授权预设使用方
  → 运行期：注入 BK_PLUGIN_APIGW_NAME 环境变量
  → 使用方经 get_deployed_statuses() 发现插件与访问地址，经网关调用
```

**能力分层小结**：
- **应用层（不依赖运行时 CR 类型）**：distributor 授权、profile、网关注册、环境变量注入 —— 替换运行时后照常工作。
- **运行时层（依赖部署产物）**：`get_deployed_statuses` 的部署状态判断与地址解析 —— 依赖「成功 Release + Service/Ingress」，替换 SandboxInstance 运行时时需保证这条链路成立。
