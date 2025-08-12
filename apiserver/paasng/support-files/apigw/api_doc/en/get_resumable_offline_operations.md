### Description
Query resumable offline operations. Resumable offline operation means stuck offline operation. 

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

### Response Result Example
#### Success Response
When there are resumable offline operation
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

when there are no resumable offline operation
```json
{}
```

### Response Result Parameter Description

| Field |   Type | Description |
| ------ | ------ | ------ | 
| id | string | UUID |
| status | string | Offline status, optional values: successful, failed, pending |
| operator | object | Operator |
| created | string | Created |
| log | string | Offline log |
| err_detail | string | Offline exception reason |
| offline_operation_id | string | Offline operation ID |
| environment | string | Environment name |
| repo | object | Repository information |

repo
| Field |   Type | Description |
| ------ | ------ | ------ |
| source_type | string | Source type |
| type | string | Type |
| name | string | Name |
| url | string | URL |
| revision | string | Revision |
| comment | string | Comment |