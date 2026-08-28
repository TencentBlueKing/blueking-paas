### 功能描述
查看应用模块的环境变量列表（不含平台内置变量）。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| environment_name | string | 否 | 按生效环境过滤：stag / prod / _global_ |
| order_by | string | 否 | 排序方式，默认 "-created"，可选 "key" |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/
```

### 返回结果示例
```json
[
    {
        "id": 12,
        "key": "DEBUG",
        "value": "true",
        "environment_name": "_global_",
        "is_global": true,
        "is_sensitive": false,
        "description": "debug switch",
        "is_builtin": false
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 变量 ID |
| key | string | 变量名，须匹配 `[A-Z][A-Z0-9_]*` |
| value | string | 变量值；`is_sensitive=true` 时会被掩码为 `******` |
| environment_name | string | 生效环境：stag / prod / _global_ |
| is_global | boolean | 是否对所有环境生效 |
| is_sensitive | boolean | 是否敏感 |
| description | string | 变量描述 |
