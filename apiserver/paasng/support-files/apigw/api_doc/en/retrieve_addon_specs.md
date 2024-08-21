### Description
Retrieve the specification combinations of enhanced services

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code       | string         | Yes      | Application ID, e.g. "apigw-api-test" |
| module         | string         | Yes      | Module name, e.g. "default" |
| service_id     | string         | Yes      | Service ID, e.g. "946ee404-df67-4013-a92f-9cc116ff50dc" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/modules/default/services/946ee404-df67-4013-a92f-9cc116ff50dc/specs/
```

### Response
#### Success Response
If the specifications are configured
```json
{
    "results": {
        "version": "5.7",
        "app_zone": "universal"
    }
}
```

If the specifications are not configured
```json
{
    "results": {
    }
}
```

### Response Parameters Description

| Field             | Type   | Description      |
| ----------------- | ------ | ---------------- |
| results           | dict   | Returned data    |
| results.version   | string | Version information |
| results.app_zone  | string | Application area |