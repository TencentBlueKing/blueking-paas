### Description

List MCP servers with system API credentials.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |

### Request example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/
```

### Response example

```json
[
    {
        "mcp_server": {
            "id": 1,
            "name": "perm-management",
            "title": "PaaS permission management",
            "description": "Query gateways and apply for resource permissions",
            "tools_count": 5,
            "doc_link": "https://example.com/doc",
            "tool_names": ["list_gateways", "apply_permission"],
            "protocol_type": "streamable_http",
            "url": "https://example.com/mcp",
            "categories": [{"name": "Official", "display_name": "Official"}],
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

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| mcp_server | object | MCP server basic info |
| mcp_server.id | integer | MCP server ID |
| mcp_server.name | string | MCP server name |
| mcp_server.title | string | MCP server display name |
| mcp_server.description | string | MCP server description |
| mcp_server.tools_count | integer | Number of tools |
| mcp_server.doc_link | string | Document link |
| mcp_server.tool_names | list | Tool names |
| mcp_server.protocol_type | string | Protocol type |
| mcp_server.url | string | MCP server access URL |
| mcp_server.categories | list | Categories |
| mcp_server.is_official | boolean | Whether it is an official MCP server |
| mcp_server.oauth2_public_client_enabled | boolean | Whether OAuth2 public client mode is enabled |
| mcp_server.oauth2_personal_client_enabled | boolean | Whether OAuth2 personal client mode is enabled |
| permission | object | Permission of the application on this MCP server |
| permission.status | string | Permission status (e.g. need_apply / pending / owned) |
| permission.action | string | Available action (apply / renew, etc.) |
| permission.expires_in | integer | Remaining validity in seconds, null means unlimited |
| permission.handled_by | list | Approvers |
| permission.approval_url | string | Permission approval link |
