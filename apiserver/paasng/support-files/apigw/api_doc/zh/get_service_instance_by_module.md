### 功能描述
获取指定应用、模块和服务的详细信息，包括服务实例配置、凭证、环境等信息。

### 请求参数

#### 1、路径参数：

| 参数名称   | 参数类型 | 必须 | 参数说明                                           |
| ---------- | -------- | ---- | -------------------------------------------------- |
| app_code   | string   | 是   | 应用 ID                            |
| module     | string   | 是   | 模块名称，如 "default"                             |
| service_id | string   | 是   | 增强服务 ID |

#### 2、接口参数：
暂无

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/cloud4paas/modules/default/services/a31e476d-5ec0-29b0-564e-5f81b5a5ef32/
```

### 返回结果示例
```json
{
    "count": 1,
    "results": [
        {
            "service_instance": {
                "config": {
                    "bk_monitor_space_id": "bksaas__appid1",
                    "bk_app_code": "appid1",
                    "app_name": "bkapp_appid1_stag_91",
                    "env": "stag",
                    "admin_url": "https://bkm.example.com/?space_uid=bksaas__appid1#/apm/application?filter-app_name=bkapp_appid1_stag_91"
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
        "prod": {
            "name": "default-otel",
            "description": "otel service"
        },
        "stag": {
            "name": "default-otel",
            "description": "otel service"
        }
    }
}
```

### 返回结果参数说明
| 字段                                                   | 类型   | 是否必填 | 描述                                  |
| ------------------------------------------------------ | ------ | -------- | ------------------------------------- |
| count                                                  | int    | 是       | 返回结果的数量                        |
| results                                                | list   | 是       | 服务实例的详细信息列表                |
| results[0].service_instance                            | dict   | 是       | 服务实例的具体信息                    |
| results[0].service_instance.config                     | dict   | 是       | 服务实例的配置信息                    |
| results[0].service_instance.credentials                | string | 是       | 服务实例的凭证信息（JSON 格式字符串） |
| results[0].service_instance.sensitive_fields           | list   | 是       | 敏感字段列表                          |
| results[0].service_instance.hidden_fields              | dict   | 是       | 隐藏字段字典                          |
| results[0].environment                                 | string | 是       | 环境标识，如 "stag"                   |
| results[0].environment_name                            | string | 是       | 环境名称，如 "预发布环境"             |
| results[0].usage                                       | dict   | 是       | 服务实例的使用信息                    |
| plans                                                  | dict   | 是       | 不同环境的增强服务 Plan               |
| plans[env].name                                        | string | 是       | 增强服务 Plan 名称                              |
| plans[env].description                                 | string | 是       | 增强服务 Plan 描述                              |