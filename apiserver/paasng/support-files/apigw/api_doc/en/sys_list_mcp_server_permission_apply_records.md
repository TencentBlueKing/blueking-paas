### Description

List MCP server permission apply records with system API credentials.

#### Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be managed by the caller |

#### Query parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| applied_by | string | No | Applicant |
| applied_time_start | integer | No | Apply start time (Unix timestamp) |
| applied_time_end | integer | No | Apply end time (Unix timestamp) |
| apply_status | string | No | Apply status |
| query | string | No | Keyword matching the MCP server name |

### Request example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/permissions/apply-records/?apply_status=pending
```

### Response example

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "mcp_server": {"id": 1, "name": "perm-management", "title": "PaaS permission management"},
            "id": 12,
            "bk_app_code": "ai-demo",
            "applied_by": "admin",
            "applied_time": "2026-01-01T10:00:00+08:00",
            "handled_by": "",
            "handled_time": null,
            "status": "pending",
            "status_display": "Pending",
            "comment": "",
            "reason": "Need to call this MCP server",
            "expire_days": 180,
            "approval_url": "https://example.com/approval/12"
        }
    ]
}
```

### Response fields

| Field | Type | Description |
| --- | --- | --- |
| count | integer | Total count |
| next | string | Next page link, null when there is no more data |
| previous | string | Previous page link, null on the first page |
| results | list | Apply records |
| results[].mcp_server | object | Related MCP server info |
| results[].mcp_server.id | integer | MCP server ID |
| results[].mcp_server.name | string | MCP server name |
| results[].mcp_server.title | string | MCP server display name |
| results[].id | integer | Apply record ID |
| results[].bk_app_code | string | Application ID |
| results[].applied_by | string | Applicant |
| results[].applied_time | string | Applied time |
| results[].handled_by | string | Handler |
| results[].handled_time | string | Handled time, empty when pending |
| results[].status | string | Approval status |
| results[].status_display | string | Display text of approval status |
| results[].comment | string | Approval comment |
| results[].reason | string | Apply reason |
| results[].expire_days | integer | Requested validity in days |
| results[].approval_url | string | Approval ticket link |
