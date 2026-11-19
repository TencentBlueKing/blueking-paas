### 功能描述

以应用身份批量申请 MCP Server 权限。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |

#### 请求体

```json
{
    "mcp_server_ids": [1, 2],
    "reason": "需要调用该 MCP Server",
    "applied_by": "admin",
    "operator": "admin"
}
```

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| mcp_server_ids | list[int] | 是 | MCP Server ID 列表 |
| reason | string | 是 | 申请原因 |
| applied_by | string | 是 | 申请人用户名，传递给网关记录为申请单的申请人 |
| operator | string | 是 | 操作人用户名，仅记入 PaaS 操作记录，允许使用虚拟账号 |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"mcp_server_ids": [1, 2], "reason": "需要调用该 MCP Server", "applied_by": "admin", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/permissions/apply/
```

### 返回结果示例

```json
(204 No Content)
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| (无) | - | 成功时返回 204，无响应体 |
