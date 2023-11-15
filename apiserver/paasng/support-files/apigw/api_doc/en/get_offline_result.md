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

#### Get your access_token

Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### Response Result Example
```json
{
    "status": "str",
    "error_detail": "str",
    "logs": "str"
}
```

### Response Result Parameter Description

| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| status | string | Yes | Offline task status (successful, pending, or failed) |
| error_detail | string | Yes | Error information |
| logs | string | Yes | Offline log |