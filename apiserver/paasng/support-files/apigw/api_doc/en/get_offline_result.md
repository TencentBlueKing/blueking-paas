### Function Description
Query the result of the offline task

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID |
| module   | string | Yes | Module name, such as "default" |
| offline_operation_id | string | Yes | UUID of the offline task |

#### 2. API Parameters:
None.


### Request Example
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AppCode}}/modules/{{Fill in your module name}}/envs/{Fill in App deployment environment:stag or prod}/offlines/{{offline_operation_id}}/result/
```

### Response Result Example
```json
{
    "id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "status": "successful",
    "operator": {
        "id": "0336c3a7948c4299b7",
        "username": "bk-apigw",
        "provider_type": 3,
        "avatar": ""
    },
    "created": "2024-08-19 11:30:26",
    "log": "offline succeeded.",
    "err_detail": null,
    "offline_operation_id": "4e69986f-00e8-41ad-bef9-8ac82201ae07",
    "environment": "stag",
    "repo": {
        "source_type": "bare_git",
        "type": "branch",
        "name": "master",
        "url": "https://gitee.com/example.git",
        "revision": "f0904787f2df1f55b96aed52f2896c0ce8f97c29",
        "comment": ""
    }
}
```

### Response Result Parameter Description

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