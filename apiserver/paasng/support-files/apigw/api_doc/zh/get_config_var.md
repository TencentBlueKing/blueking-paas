### 功能描述
通过 key 查询环境变量。同一 key 可能在 stag / prod / _global_ 各有一条，因此返回数组。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |
| module | string | 是 | 模块名称，如 "default" |
| config_var_key | string | 是 | 环境变量名，如 "FOO"。须匹配 `[A-Z][A-Z0-9_]*` |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/FOO/
```

### 返回结果示例
```json
[
    {
        "id": 12,
        "key": "FOO",
        "value": "bar",
        "environment_name": "stag",
        "is_global": false,
        "is_sensitive": false,
        "description": "foo var"
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 变量 ID |
| key | string | 变量名 |
| value | string | 变量值；敏感值会被掩码 |
| environment_name | string | 生效环境：stag / prod / _global_ |
| is_global | boolean | 是否对所有环境生效 |
| is_sensitive | boolean | 是否敏感 |
| description | string | 变量描述 |
