### Function Description  
Update or Create Environment Variable Values for an Application  

### Request Parameters  

#### 1. Path Parameters:  
| Parameter Name | Parameter Type | Required | Parameter Description |  
| ------------ | ------------ | ------ | ---------------- |  
| app_code | string | Yes | Application ID, e.g., "appid1" |  
| module | string | Yes | Module name, e.g., "default" |  
| config_key | string | Yes | Configuration variable name, e.g., "KEY1" |  

#### 2. Interface Parameters:  
| Parameter Name | Parameter Type | Required | Parameter Description |  
| ------------ | ------------ | ------ | ---------------- |  
| environment_name | string | Yes | Environment (stag for pre-production, prod for production) |  
| value | string | Yes | Value of the environment variable |  
| description | string | Yes | Description of the environment variable |  

### Request Example  
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{    "environment_name": "stag",    "value": "0.0.1",    "description": "d0.0.1 version"}' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/KEY1/
```  

### Response Example  

**Status Code Explanation:**  
- **201**: Configuration variable created or updated successfully