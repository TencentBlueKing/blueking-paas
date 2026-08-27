### 功能描述
查看应用模块的增强服务，一次返回已绑定（bound）、共享（shared）和未绑定（unbound）三类。

绑定前先调本接口，用服务英文名（如 `mysql` / `redis`）在 `unbound` 中找到 `uuid`，再调用 `bind_service`。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/services/
```

### 返回结果示例
```json
{
    "bound": [
        {
            "service": {
                "uuid": "73f77c3a-dbc8-44cf-a6c5-3b1d656c4206",
                "name": "mysql",
                "display_name": "MySQL",
                "description": "MySQL database"
            },
            "provision_infos": {"stag": true, "prod": false},
            "plans": {
                "stag": {"name": "default", "description": "default plan"},
                "prod": {"name": "default", "description": "default plan"}
            },
            "ref_modules": []
        }
    ],
    "shared": [],
    "unbound": [
        {
            "uuid": "1f80d0b7-97ac-462f-9059-839666c971bc",
            "name": "redis",
            "display_name": "Redis",
            "description": "Redis cache"
        }
    ]
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| bound | list | 本模块已启用的增强服务 |
| bound[].service.uuid | string | 增强服务 UUID |
| bound[].service.name | string | 服务英文名 |
| bound[].provision_infos | object | stag / prod 是否已分配实例 |
| shared | list | 从其他模块共享来的服务 |
| unbound | list | 可见但尚未绑定的服务，绑定请使用这里的 uuid |
