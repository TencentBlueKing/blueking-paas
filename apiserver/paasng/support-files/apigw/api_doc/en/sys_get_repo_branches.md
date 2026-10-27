### Description

Retrieve the List of Code Repository Branches for an Application Module with system API credentials.

The response structure is the same as the user-facing `get_repo_branches` API.

### Request Parameters

#### 1. Path parameters

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| app_code | string | Yes | Application ID, must be an AI Agent application |
| module | string | Yes | Module name, e.g. "default" |

#### 2. Query parameters

None.

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/repo/branches/
```

### Response Example

```json
{
    "results": [
        {
            "name": "master",
            "type": "branch",
            "display_type": "branch",
            "revision": "31736e690ba0bfa7a81d3730ed6544b3566b3f19",
            "url": "http://git.example.com/ai-demo.git",
            "last_update": "2024-09-10 16:48:24",
            "message": "init repo",
            "extra": {}
        }
    ]
}
```

### Response Parameters

| Name | Type | Description |
| --- | --- | --- |
| results | list | List of branches and tags |
| results[].name | string | Branch name |
| results[].type | string | Version type (branch / tag) |
| results[].display_type | string | Display type (branch / tag) |
| results[].revision | string | Latest commit hash |
| results[].url | string | Repository url |
| results[].last_update | string | Last update time |
| results[].message | string | Last commit message |
| results[].extra | object | Extra information |
