### Resource Description
App deployment interface

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|
|   env | string |yes| Environment name, optional values "stag"/"prod"|

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   url   |   string     |   yes   | Deployment source path (including source code)    |
|   revision |   string     |   yes   | Source warehouse version No.|
|   version_name | string |yes| Name of branch or tag|
|   version_type | string |yes| For svn, transfer/tag is supported; For git, transfer is supported|

### Call example

#### gitlab

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "RLjqb3t0VQ5v2ZuT0rXhz7413rKSr3"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{Fill in your AppCode}/modules/default/envs/{Fill in the App deployment environment:stag或prod}/deployments/ -d '{"url": "http://git.example.com/Your project path.git", "revision": "commit sha value", "version_type": "branch", "version_name": "master"}' -H 'Content-Type: application/json'
```

### Return result
```json
{
    "stream_url": "/streams/22d0e9c8-9cfc-45a5-b5a8-718137c515db",
	"deployment_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Return result description
|   Field   | Type | Description                     |
| ------------ | ---------- | ------------------------------ |
|  stream_url  |     string  |     Deployment log output stream ID          |
|     deployment_id | string  | Deployment Operation ID |