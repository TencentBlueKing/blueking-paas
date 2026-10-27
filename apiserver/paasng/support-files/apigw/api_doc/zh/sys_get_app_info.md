### 功能描述

以应用身份查询 AI Agent 应用的信息、部署模式与访问地址。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

#### 租户说明

应用态接口不依赖用户登录态，租户通过 `X-Bk-Tenant-Id` 请求头传递：

- 全租户应用（`app_tenant_mode` 为 `global`）对所有租户可用；
- 单租户应用仅在其 `app_tenant_id` 对应租户下可用，其余租户返回 403 `APP_TENANT_MISMATCH`；
- 未开启多租户模式时忽略该请求头。

### 请求参数

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/
```

### 返回结果示例

```json
{
    "application": {
        "id": "c4b6f5c1d3a2410d8f9c2b7e5a6d1f30",
        "code": "ai-demo",
        "name": "智能体示例",
        "name_en": "",
        "type": "cloud_native",
        "is_ai_agent_app": true,
        "is_plugin_app": true,
        "deploy_policy": "default",
        "app_tenant_mode": "single",
        "app_tenant_id": "default",
        "language": "Python",
        "region": "default",
        "logo_url": "http://example.com/logo.png",
        "deploy_info": {
            "stag": {
                "deployed": true,
                "url": "http://ai-demo-stag.example.com"
            },
            "prod": {
                "deployed": false,
                "url": ""
            }
        },
        "preferred_prod_url": null,
        "modules": [
            {
                "id": "1f0a6c7e9b2d4d8fa1c3e5b7d9f0a2c4",
                "name": "default",
                "is_default": true,
                "source_origin": 7,
                "web_config": {
                    "engine_enabled": true,
                    "can_create_extra_modules": false
                }
            }
        ]
    },
    "web_config": {
        "engine_enabled": true,
        "can_create_extra_modules": false,
        "confirm_required_when_publish": false,
        "market_published": false
    },
    "migration_status": {
        "status": "no_need_migration",
        "error_msg": ""
    }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| application | object | 应用信息，与用户态接口 `get_app_info` 的 `application` 一致，额外包含 `deploy_info` / `preferred_prod_url` |
| application.deploy_policy | string | 部署模式，`default` 表示普通部署，`isolated` 表示隔离环境部署 |
| application.deploy_info | object | 各环境的部署状态与访问地址，key 为环境名（stag / prod） |
| application.preferred_prod_url | string | 首选的生产环境访问地址，未配置自定义域名时为 null |
| web_config | object | 应用级功能开关 |
| migration_status | object | 云原生迁移状态，`status` 为 `no_need_migration` 时表示无需迁移 |
