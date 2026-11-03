### 功能描述

以应用身份查询 MCP Server 列表。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/
```

### 返回结果示例

```json
[
    {
        "mcp_server": {
            "id": 1,
            "name": "perm-management",
            "title": "PaaS 平台权限管理",
            "description": "查询网关及资源，申请、续期网关资源权限",
            "tools_count": 5,
            "doc_link": "https://example.com/doc",
            "tool_names": ["list_gateways", "apply_permission"],
            "protocol_type": "streamable_http",
            "url": "https://example.com/mcp",
            "categories": [{"name": "Official", "display_name": "官方"}],
            "is_official": true,
            "oauth2_public_client_enabled": false,
            "oauth2_personal_client_enabled": false
        },
        "permission": {
            "status": "need_apply",
            "action": "apply",
            "expires_in": null,
            "handled_by": ["admin"],
            "approval_url": ""
        }
    }
]
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| mcp_server | object | MCP Server 基本信息 |
| mcp_server.id | integer | MCP Server ID |
| mcp_server.name | string | MCP Server 名称 |
| mcp_server.title | string | MCP Server 展示名称 |
| mcp_server.description | string | MCP Server 描述 |
| mcp_server.tools_count | integer | 工具数量 |
| mcp_server.doc_link | string | 文档访问地址 |
| mcp_server.tool_names | list | 工具名称列表 |
| mcp_server.protocol_type | string | 协议类型 |
| mcp_server.url | string | MCP Server 访问地址 |
| mcp_server.categories | list | 分类列表 |
| mcp_server.is_official | boolean | 是否为官方 MCP Server |
| mcp_server.oauth2_public_client_enabled | boolean | 是否开启 OAuth2 公开客户端模式 |
| mcp_server.oauth2_personal_client_enabled | boolean | 是否开启 OAuth2 私有客户端模式 |
| permission | object | 当前应用对该 MCP Server 的权限信息 |
| permission.status | string | 权限状态（如 need_apply / pending / owned） |
| permission.action | string | 可执行操作（apply / renew 等） |
| permission.expires_in | integer | 权限剩余有效期（秒），为空表示无限制 |
| permission.handled_by | list | 审批人列表 |
| permission.approval_url | string | 权限审批链接 |
