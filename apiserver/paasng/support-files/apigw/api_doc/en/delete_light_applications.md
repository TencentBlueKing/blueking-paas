### Description

Delete lightweight applications, for management-side APP use only.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Lightweight APP Code  |

### Request Example
```
curl -X DELETE -H 'X-Bkapi-Authorization: {"bk_app_code": "appid", "bk_app_secret": "***"}' --insecure 'http://bkapi.example.com/api/bkpaas3/prod/system/light-applications?light_app_code=bk_sops_xxxxx'
```

### Response Result Example

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "count": 1
  },
  "result": true
}
```

### Response Result Parameter Description

| Field  | Type | Description      |
| ------ | ---- | ---------------- |
| count  | int  | Deleted app count |