### Description
Get light application information.

Note: By default, only Standard Operation (app ID: bk_sops) is allowed to call the APIs related to light apps, if you need to call them, please contact the platform administrator to add permissions.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| light_app_code | string         | Yes      | Light Application APP Code |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/light-applications?light_app_code=demo-0727-001_ps
```

### Response Result Example
```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "light_app_code": "demo-0727-001_ps",
    "app_name": "demo-0727-001_ps",
    "app_url": "http://app.demo.com",
    "introduction": "Test application",
    "creator": "admin",
    "logo": "http://demo.com/app-logo/o_demo-0727-001_ps.png",
    "developers": [
      "admin"
    ],
    "state": 4
  },
  "result": true
}
```

### Response Result Parameter Description
| Name          | Type   | Description         |
| ------------- | ------ | ------------------- |
| light_app_code| string | Light Application APP Code |
| app_name      | string | Light Application Name |
| app_url       | string | Application Link |
| introduction  | string | Application Introduction |
| creator       | string | Creator |
| logo          | string | Icon URL |
| developers    | array  | Developer List |
| state         | int    | Application Status |