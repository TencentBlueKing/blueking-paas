### Resource Description
Query app module environment deployment information

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_info/
```

### Request parameter Description

| Name                                | Description |
| ----------------------------------- | ----------- |
| code * <br/>string<br/>(path)       | code        |
| environment *<br/>string<br/>(path) | environment |
| module_name *<br/>string<br/>(path) | module_name |

### Return result
```json
{
  "deployment": {
    "id": "--",
    "status": "--",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": "--",
    "deployment_id": "--",
    "environment": "--",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": ""
    }
  },
  "exposed_link": {
    "url": "--"
  }
}
```