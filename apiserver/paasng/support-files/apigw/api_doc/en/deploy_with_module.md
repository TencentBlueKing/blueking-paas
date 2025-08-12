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
| revision       | string         | Yes      | Source code repository version number |
| version_name   | string         | Yes      | Branch or tag name |
| version_type   | string         | Yes      | For svn, supports passing trunk / tag; for git, supports passing branch |

Make sure that revision, version_name, and version_type can be found in the corresponding repository.

### Request Example

#### gitlab

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{Fill in your AppCode}/modules/default/envs/{Fill in App deployment environment: stag or prod}/deployments/ -d '{"revision": "Source code repository version number", "version_type": "Branch or tag name", "version_name": "For svn, supports passing trunk / tag; for git, supports passing branch"}' -H 'Content-Type: application/json'
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