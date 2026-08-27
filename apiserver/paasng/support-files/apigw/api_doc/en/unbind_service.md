### Description
Unbind an addon service from an application module and recycle provisioned instances.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description                    |
| -------------- | -------------- | -------- | ------------------------------ |
| app_code       | string         | Yes      | Application ID                 |
| module         | string         | Yes      | Module name, e.g. "default"    |
| service_id     | string         | Yes      | addOns service ID              |

#### 2. API Parameters:
None.

### Request Example
```
curl -X DELETE -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/services/a31e476d-5ec0-29b0-564e-5f81b5a5ef32/
```

### Response Example

**Status Code Explanation:**
- **200**: Unbound successfully (empty body)
- **404**: The module is not bound to this service
