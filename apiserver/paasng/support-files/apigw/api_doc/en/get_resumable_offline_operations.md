### Description
Query resumable offline operations

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID |
| module   | string | Yes | Module name, e.g. "default" |
| env | string | Yes | Environment name, optional values: "stag" / "prod" |

#### 2. API Parameters:
None.

### Request Example

#### svn
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AppCode}}/modules/{{Fill in your module name}}/envs/{Fill in App deployment environment:stag or prod}/offlines/resumable/
```

#### Get your access_token
Before calling the interface, please obtain your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)


### Response Result Example
```json
{
  "result": {
    "id": "--",
    "status": "successful",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": datetime,
    "log": "try to stop process:web ...success to stop process: web\nall process stopped.\n",
    "err_detail": null,
    "offline_operation_id": "01e3617a-96b6-4bf3-98fb-1e27fc68c7ee",
    "environment": "stag",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": "--"
    }
  }
}
```

### Response Result Parameter Description

| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| id | string | Yes | UUID |
| status | string | Yes | Offline status, optional values: successful, failed, pending |
| operator | string | Yes | Operator |
| created | string | Yes | Created |
| log | string | Yes | Offline log |
| err_detail | string | Yes | Offline exception reason |
| offline_operation_id | string | Yes | Offline operation ID |
| environment | string | Yes | Environment name |
| repo | object | Yes | Repository information |

repo
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| source_type | string | Yes | Source type |
| type | string | Yes | Type |
| name | string | Yes | Name |
| url | string | Yes | URL |
| revision | string | Yes | Revision |
| comment | string | Yes | Comment |