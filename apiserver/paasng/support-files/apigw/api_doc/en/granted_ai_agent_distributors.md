### Function Description  
Authorize the AI plugin application for plugin users.  

### Request Parameters  

#### 1. Path Parameters:  

| Parameter Name   | Parameter Type | Required | Parameter Description                           |
| ---------------- | -------------- | -------- | ----------------------------------------------- |
| code             | string         | Yes      | Application ID                                  |
| distributor_code | string         | Yes      | Application ID corresponding to the plugin user |

#### 2. Interface Parameters:  
None.  

### Request Example  

```bash
curl -X POST \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' \
  -d '{}' \
  --insecure \
  https://bkapi.example.com/prod/system/bk_plugins/ai/ai-test/granted_distributors/bkchat/
```

### Return Result Example  

```json
[
    {
        "code_name": "bkchat",
        "name": "bkchat",
        "introduction": null
    }
]
```

### Return Result Parameter Description  

| Field        | Type           | Required | Description                     |
| ------------ | -------------- | -------- | ------------------------------- |
| code_name    | string         | Yes      | English name of the plugin user |
| name         | string         | Yes      | Name of the plugin user         |
| introduction | null or string | No       | Brief introduction of the user  |