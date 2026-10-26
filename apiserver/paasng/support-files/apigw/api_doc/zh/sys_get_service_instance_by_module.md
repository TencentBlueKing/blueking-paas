### 功能描述

以应用身份查询 AI Agent 应用模块绑定的增强服务实例，其中包括可观测性入口 `admin_url`。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

返回结构与用户态接口 `get_service_instance_by_module` 一致，模块与增强服务未绑定时返回 404。

#### 租户说明

应用态接口不依赖用户登录态，租户通过 `X-Bk-Tenant-Id` 请求头传递：

- 全租户应用（`app_tenant_mode` 为 `global`）对所有租户可用；
- 单租户应用仅在其 `app_tenant_id` 对应租户下可用，其余租户返回 403 `APP_TENANT_MISMATCH`；
- 未开启多租户模式时忽略该请求头。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| module | string | 是 | 模块名称，如 "default" |
| service_id | string | 是 | 增强服务 ID |

#### 2、接口参数

无。

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/services/a31e476d-5ec0-29b0-564e-5f81b5a5ef32/
```

### 返回结果示例

```json
{
    "count": 1,
    "results": [
        {
            "service_instance": {
                "config": {
                    "bk_monitor_space_id": "bksaas__ai-demo",
                    "bk_app_code": "ai-demo",
                    "app_name": "bkapp_ai-demo_stag",
                    "env": "stag",
                    "admin_url": "https://bkm.example.com/?space_uid=bksaas__ai-demo#/apm/application"
                },
                "credentials": "{}",
                "sensitive_fields": [],
                "hidden_fields": {}
            },
            "environment": "stag",
            "environment_name": "预发布环境",
            "usage": "{}"
        }
    ],
    "plans": {
        "stag": {
            "name": "default-otel",
            "description": "otel service"
        }
    }
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| count | int | 返回结果的数量 |
| results | list | 服务实例的详细信息列表 |
| results[].service_instance.config | object | 服务实例配置，**可观测性入口为其中的 `admin_url` 字段** |
| results[].service_instance.credentials | string | 服务实例凭证（JSON 格式字符串，敏感字段已隐藏） |
| results[].service_instance.sensitive_fields | list | 敏感字段列表 |
| results[].service_instance.hidden_fields | object | 隐藏字段 |
| results[].environment | string | 环境标识，如 "stag" |
| results[].environment_name | string | 环境名称 |
| results[].usage | string | 服务实例的使用信息 |
| plans | object | 各环境的增强服务 Plan，key 为环境名 |
