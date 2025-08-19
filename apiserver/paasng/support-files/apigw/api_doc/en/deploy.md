### Description
App deployment interface for deploying applications to a specified environment.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| url            | string         | Yes      | Deployment source code path (including trunk) |
| revision       | string         | Yes      | Source code repository version number |
| version_name   | string         | Yes      | Name of the branch or tag |
| version_type   | string         | Yes      | For svn, supports trunk / tag; for git, supports branch |


### Request Example

#### gitlab
```bash
curl --cookie "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;" -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' -H 'X-CSRFToken: HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{Fill in your AppCode}/envs/{Fill in App deployment environment: stag or prod}/deployments/ -d '{"url": "http://gitlab.example.com/your_project_path.git", "revision": "commit sha value", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### Response Example
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Response Parameter Description
| Parameter Name | Parameter Type | Parameter Description |
| -------------- | -------------- | --------------------- |
| stream_url     | string         | Deployment log output stream ID |
| deployment_id  | string         | Deployment operation ID |