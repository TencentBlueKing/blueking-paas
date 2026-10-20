### Function Description

Query the deployment result of an AI Agent application using application credentials. The caller must have the AIDEV system role, and the target application must be an AI Agent application, otherwise 403 is returned.

The response is the same as the user-facing API `get_deployment_result`.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an AI Agent application |
| module | string | Yes | Module name |
| deployment_id | string | Yes | Deployment task ID |

#### 2. Interface Parameters

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| include_ansi_codes | boolean | No | Whether to keep ANSI escape codes in logs. Default false. |

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/deployments/22d0e9c8-9cfc-45a5-b5a8-718137c515db/result/
```

### Response Example

```json
{
    "status": "failed",
    "logs": "\nProcfile error: ...",
    "error_detail": "Procfile error: ...",
    "error_tips": {
        "matched_solutions_found": false,
        "possible_reason": "Temporarily unable to find a solution, please go to the \"Standard Output Log\" to check for exceptions",
        "helpers": [{
            "text": "Log Query",
            "link": "http://bkpaas.example.com/developer-center/apps/appid/default/log?tab=stream"
        }]
    }
}
```

### Response Parameter Description

| Field | Type | Description |
| ------- | ------ | ------------- |
| status | string | Deployment status |
| logs | string | Deployment logs, plain text |
| error_detail | string | Error details |
| error_tips.matched_solutions_found | boolean | Whether there are matched tips |
| error_tips.possible_reason | string | Possible reasons for deployment errors |
| error_tips.helpers | object | Auxiliary information, including text and links |
