### 功能描述

以应用身份查询网关下可申请的接口列表，同时返回当前应用对每个接口的权限状态。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |
| gateway_name | string | 是 | 网关名称 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/gateways/paasv3/permissions/resources/
```

### 返回结果示例

```json
[
    {
        "id": 1,
        "name": "create_app",
        "gateway_name": "paasv3",
        "gateway_id": 1,
        "description": "创建应用",
        "description_en": "Create application",
        "expires_in": null,
        "permission_level": "resource",
        "permission_status": "need_apply",
        "permission_action": "apply",
        "doc_link": "https://example.com/docs"
    }
]
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| id | integer | 资源 ID |
| name | string | 接口名称 |
| gateway_name | string | 网关名称 |
| gateway_id | integer | 网关 ID |
| description | string | 接口描述 |
| description_en | string | 接口英文描述 |
| expires_in | integer | 权限剩余有效期（秒），为空表示无限制 |
| permission_level | string | 权限级别 |
| permission_status | string | 当前应用的权限状态 |
| permission_action | string | 可执行操作（apply / renew） |
| doc_link | string | 接口文档链接 |
