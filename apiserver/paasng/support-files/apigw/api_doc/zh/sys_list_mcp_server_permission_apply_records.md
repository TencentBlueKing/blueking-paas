### 功能描述

以应用身份查询 MCP Server 权限申请记录，用于获取申请状态。

#### 路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| app_code | string | 是 | 应用 ID，必须归调用方管理 |

#### 接口参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| --- | --- | --- | --- |
| applied_by | string | 否 | 申请人 |
| applied_time_start | integer | 否 | 申请开始时间（Unix 时间戳） |
| applied_time_end | integer | 否 | 申请截止时间（Unix 时间戳） |
| apply_status | string | 否 | 申请状态 |
| query | string | 否 | 搜索条件，支持模糊匹配 MCPServer 名称 |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/cloudapi_v2/bkapps/applications/ai-demo/mcp-servers/permissions/apply-records/?apply_status=pending
```

### 返回结果示例

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "mcp_server": {"id": 1, "name": "perm-management", "title": "PaaS 平台权限管理"},
            "id": 12,
            "bk_app_code": "ai-demo",
            "applied_by": "admin",
            "applied_time": "2026-01-01T10:00:00+08:00",
            "handled_by": "",
            "handled_time": null,
            "status": "pending",
            "status_display": "待审批",
            "comment": "",
            "reason": "需要调用该 MCP Server",
            "expire_days": 180,
            "approval_url": "https://example.com/approval/12"
        }
    ]
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| --- | --- | --- |
| count | integer | 总条数 |
| next | string | 下一页链接，无更多数据时为 null |
| previous | string | 上一页链接，无上一页时为 null |
| results | list | 申请记录列表 |
| results[].mcp_server | object | 关联的 MCP Server 信息 |
| results[].mcp_server.id | integer | MCP Server ID |
| results[].mcp_server.name | string | MCP Server 名称 |
| results[].mcp_server.title | string | MCP Server 展示名称 |
| results[].id | integer | 申请记录 ID |
| results[].bk_app_code | string | 申请应用 ID |
| results[].applied_by | string | 申请人 |
| results[].applied_time | string | 申请时间 |
| results[].handled_by | string | 处理人 |
| results[].handled_time | string | 处理时间，未处理时为空 |
| results[].status | string | 审批状态 |
| results[].status_display | string | 审批状态展示文案 |
| results[].comment | string | 审批备注 |
| results[].reason | string | 申请原因 |
| results[].expire_days | integer | 申请的有效期（天） |
| results[].approval_url | string | 审批单据链接 |
