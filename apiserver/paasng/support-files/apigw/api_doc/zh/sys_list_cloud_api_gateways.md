### 功能描述

以应用身份查询网关列表。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/
```

### 返回结果示例

```json
[
    {
        "id": 1,
        "name": "paasv3",
        "description": "PaaS 平台网关",
        "maintainers": ["admin"],
        "doc_maintainers": {}
    }
]
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| id | integer | 网关 ID |
| name | string | 网关名称 |
| description | string | 网关描述 |
| maintainers | list | 维护人列表 |
| doc_maintainers | object | 文档维护人 |
