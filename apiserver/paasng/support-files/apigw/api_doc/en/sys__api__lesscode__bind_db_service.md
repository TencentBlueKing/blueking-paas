### Description
Attempt to bind the database enhanced service

Note: By default, only Blueking O&M development platform (app ID: bk_lesscode) is allowed to call the APIs related to light apps, if you need to call them, please contact the platform administrator to add permissions.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code       | string         | Yes      | Application ID, e.g. "apigw-api-test" |
| module         | string         | Yes      | Module name, e.g. "default" |

#### 2. API Parameters:
None.

### Request Example
```
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/appid1/modules/default/lesscode/bind_db_service
```

### Response Result Example
Reponse body is None when success.