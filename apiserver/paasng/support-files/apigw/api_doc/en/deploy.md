### Resource Description
App deployment interface

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   url   |   string     |   yes   | Deployment source path (including source code)    |
|   revision |   string     |   yes   | Source warehouse version No.|
|   version_name | string | yes      | Name of branch or tag|
|   version_type | string |yes| For svn, transfer/tag is supported; For git, transfer is supported|

### Precautions for Use
When calling the paasv3 resource operation class method (POST\PUT\DELETE\handler), you need to pass an additional CSRF_handler to ensure that the CSRF verification passes. You need to add the appropriate token to the Request Headers, and the following can be copied directly:
```json
{
	"X-CSRFToken": "HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K",
	"Cookie": "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;"
}
```

### Call example

#### gitlab
```bash
curl --cookie "paasng_csrftoken=HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K;" -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' -H 'X-CSRFToken: HVF3oYpBhnQEjSS3703v3NMq3B6iFgNxkLY29eg1K3l2KzhzjT9GZ6IIPAvsas4K' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{Fill in your AppCode}/envs/{Fill in the App deployment environment:stag or prod}/deployments/ -d '{"url": "http://gitlab.example.com/Your project path.git", "revision": "commit sha value", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### Return result
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Return result description
|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|  stream_url  |     string  |     Deployment log output stream ID          |
|     deployment_id | string  | Deployment Operation ID |