### 功能描述
绑定应用模块与增强服务。`plan_id` / `env_plan_id_map` 可不传，平台会选择默认方案。

推荐流程：先调用 `list_module_services` 拿到目标服务 `uuid`，再调用本接口。绑定后需重新部署，凭证才会注入为环境变量。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| code | string | 是 | 应用 ID |
| service_id | string | 是 | 增强服务 UUID，来自 `list_module_services` 的 `unbound[].uuid` |
| module_name | string | 否 | 模块名，不传则使用默认模块 |
| plan_id | string | 否 | 手动指定方案 ID |
| env_plan_id_map | object | 否 | 分环境方案 ID，如 `{"stag": "<plan_id>", "prod": "<plan_id>"}` |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"code":"appid1","module_name":"default","service_id":"73f77c3a-dbc8-44cf-a6c5-3b1d656c4206"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/services/service-attachments/
```

### 返回结果示例
```json
{
    "id": 1,
    "application": {
        "code": "appid1",
        "name": "demo"
    },
    "module_name": "default",
    "service": "73f77c3a-dbc8-44cf-a6c5-3b1d656c4206"
}
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 绑定关系 ID |
| application | object | 应用信息 |
| module_name | string | 模块名 |
| service | string | 增强服务 UUID |

**状态码说明：**
- **200**：绑定成功
- **400**：绑定失败，例如无可用方案或已经绑定
