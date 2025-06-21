### Function Description  
Retrieve the List of Code Repository Branches for an Application Module  

### Request Parameters  

#### 1. Path Parameters:  
| Parameter Name | Parameter Type | Required | Parameter Description |  
| ------------ | ------------ | ------ | ---------------- |  
| app_code | string | Yes | Application ID, e.g., "appid1" |  
| module | string | Yes | Module name, e.g., "default" |  

#### 2. Interface Parameters:  
None.  

### Request Example  
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{}' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/repo/branches/
```  

### Response Example  
```json
{
    "results": [
        {
            "name": "master",
            "type": "branch",
            "display_type": "branch",
            "revision": "31736e690ba0bfa7a81d3730ed6544b3566b3f19",
            "url": "http://git.example.com/app-test.git",
            "last_update": "2024-09-10 16:48:24",
            "message": "init repo",
            "extra": {}
        }
    ]
}
```  

### Response Parameter Description  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| results | list | Yes | List of branches |  

**Results Field Description:**  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| name | string | Yes | Branch name |  
| type | string | Yes | Branch type (branch/tag) |  
| display_type | string | Yes | Display type (branch/tag) |  
| revision | string | Yes | Latest commit hash of the branch |  
| url | string | Yes | Repository URL |  
| last_update | string | Yes | Last update time |  
| message | string | Yes | Commit message of the latest commit |  
| extra | dict | Yes | Additional information |  