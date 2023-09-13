### Description
App deployment interface for deploying applications to a specified environment.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name, e.g., "default" |
| env            | string         | Yes      | Environment name, available values: "stag" / "prod" |

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| url            | string         | Yes      | Deployment source code path (including trunk) |
| revision       | string         | Yes      | Source code repository version number |
| version_name   | string         | Yes      | Branch or tag name |
| version_type   | string         | Yes      | For svn, supports passing trunk / tag; for git, supports passing branch |


### Request Example

#### Get your access_token
Before calling the interface, please obtain your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

#### gitlab

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{Fill in your AppCode}/modules/default/envs/{Fill in App deployment environment: stag or prod}/deployments/ -d '{"url": "http://git.example.com/Your project path.git", "revision": "commit sha value", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### Response Result Example
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Response Result Parameter Description

| Parameter Name | Parameter Type | Parameter Description |
| -------------- | -------------- | --------------------- |
| stream_url     | string         | Deployment log output stream ID |
| deployment_id  | string         | Deployment operation ID |