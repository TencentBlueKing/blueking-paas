### Description
Query the classification list of Blueking plugins, for internal system use only.

### Request Parameters

#### 1. Path Parameters:
None

#### 2. API Parameters:
None

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugin_tags
```

### Response Result Example
```javascript
[
    {
        "code_name": "tag1",
        "name": "Category1",
        "id": 1
    }
]
```

### Response Result Parameter Description

| Field     | Type   | Description       |
| --------- | ------ | ----------------- |
| code_name | string | Category code     |
| name      | string | Category name     |
| id        | int    | Category ID       |