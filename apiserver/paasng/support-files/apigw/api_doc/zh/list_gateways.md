### 功能描述
获取可申请权限的网关列表，可用 `name` 按网关名搜索。

推荐流程：先调用本接口拿到目标网关 `name`，再调用 `list_gateway_permission_resources` 查看该网关下的资源及当前权限状态。

### 请求参数

#### 1、路径参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string | 是 | 应用 ID，如 "appid1" |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| name | string | 否 | 网关名称，如 "paasv3" |
| fuzzy | boolean | 否 | 是否按名称模糊匹配，默认 true |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/?name=paasv3&fuzzy=true'
```

### 返回结果示例
```json
[
    {
        "id": 1,
        "name": "paasv3",
        "description": "PaaS3.0 开发者中心 API 网关",
        "maintainers": ["admin"],
        "doc_maintainers": {}
    }
]
```

### 返回结果参数说明
| 字段 | 类型 | 描述 |
| ---- | ---- | ---- |
| id | int | 网关 ID |
| name | string | 网关名称 |
| description | string | 网关描述 |
| maintainers | array | 网关维护人 |
| doc_maintainers | object | 文档维护人信息 |

**状态码说明：**
- **200**：查询成功
