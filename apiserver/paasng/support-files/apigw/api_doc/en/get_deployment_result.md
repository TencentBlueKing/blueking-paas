### Description
Query deployment task results


### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name           |
| deployment_id  | string         | Yes      | Deployment task ID    |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/deployments/{deployment_id}/result/
```

### Response Result Example
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
		}, {
			"text": "Try searching in FAQ",
			"link": "https://bk.tencent.com/docs/"
		}]
	}
}
```

### Response Result Parameter Description

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| status | string | Yes | Deployment status |
| logs | string | Yes | Deployment logs, plain text |
| error_detail | string | Yes | Error details |
| error_tips.matched_solutions_found | boolean | Yes | Whether there are matched tips |
| error_tips.possible_reason | string | Yes | Possible reasons for deployment errors |
| error_tips.helpers | object | Yes | Auxiliary information, including text and links |