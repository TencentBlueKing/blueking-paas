### Resource Description
Query deployment task results

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "Your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/deployments/{deployment_id}/result/
```

### Request parameter Description
| Name                                  | Description |
| ------------------------------------- | ----------- |
| app_code * <br>string <br>(path)      | code        |
| module *<br/>string<br/>(path)        | module_name |
| deployment_id *<br/>string<br/>(path) | uuid        |



### Return result

```json
{
	"status": "failed",
	"logs": "\nProcfile error: unable to read file \"Procfile\", details: module 'paasng.dev_resources.sourcectl.package.client' has no attribute 'S3TarClient'",
	"error_detail": "Procfile error: unable to read file \"Procfile\", details: module 'paasng.dev_resources.sourcectl.package.client' has no attribute 'S3TarClient'",
	"error_tips": {
		"matched_solutions_found": false,
		"possible_reason": "No solution can be found at the moment, please go to 'Standard Output Log' to check if there are any exceptions",
		"helpers": [{
			"text": "Log query",
			"link": "http://bkpaas.example.com/developer-center/apps/appid/default/log?tab=stream"
		}, {
			"text": "Try the FAQ",
			"link": "https://bk.tencent.com/docs/"
		}]
	}
}
```

### Return result description

| status*       | string<br/>title: Status<br/>Deployment Status<br/>Enum:<br/>Array [ 3 ] |
| ------------- | ------------------------------------------------------------ |
| logs*         | string<br/>title: Logs<br/>minLength: 1<br/>Deployment log, plain text |
| error_detail* | string<br/>title: Error detail<br/>minLength: 1<br/>Error details |
| error_tips*   | dict, see the table below for field details                  |

#### error_tips Field Details：

| matched_solutions_found* | boolean <br/>title: Matched solutions found<br/>Are there any matching tips |
| ------------------------ | ------------------------------------------------------------ |
| possible_reason*         | string <br/>title: Possible reason <br/>minlength: 1<br/>possible causes of deployment errors |
| helpers*                 | { <br/>< * >:　　　　　　　　　　string<br/>}                |