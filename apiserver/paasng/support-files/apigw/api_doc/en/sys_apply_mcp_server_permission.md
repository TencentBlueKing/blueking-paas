### Description

Apply MCP server permissions in batch with system API credentials.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |

#### Request body

```json
{
    "mcp_server_ids": [1, 2],
    "reason": "Need to call this MCP server",
    "applied_by": "admin",
    "operator": "admin"
}
```

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| mcp_server_ids | list[int] | Yes | MCP server ID list |
| reason | string | Yes | Apply reason |
| applied_by | string | Yes | Applicant username, passed to the gateway as the applicant of the ticket |
| operator | string | Yes | Operator username, only recorded in PaaS audit log, virtual accounts allowed |

### Request example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"mcp_server_ids": [1, 2], "reason": "Need to call this MCP server", "applied_by": "admin", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/permissions/apply/
```

### Response example

```json
(204 No Content)
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| (none) | - | Returns 204 with no body on success |
