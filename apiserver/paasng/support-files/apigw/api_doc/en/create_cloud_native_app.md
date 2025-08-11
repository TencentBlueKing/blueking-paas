### Function Description  
Create a Cloud-Native Application  

### Request Parameters  

#### 1. Path Parameters:  
| Parameter Name | Parameter Type | Required | Parameter Description |  
| ------------ | ------------ | ------ | ---------------- |  
| app_code | string | Yes | Application ID, e.g., "monitor" |  
| module | string | Yes | Module name, e.g., "default" |  

#### 2. Interface Parameters:  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| is_plugin_app | boolean | No | Whether it is a plugin application |  
| code | string | Yes | Application ID |  
| name | string | Yes | Application name |  
| source_config | dict | Yes | Source configuration |  
| bkapp_spec | dict | Yes | Application specification |  

**Field Description for `source_config`:**  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| source_init_template | string | Yes | Source initialization template |  
| source_control_type | string | Yes | Source control type |  
| source_repo_url | string | Yes | Source repository URL |  
| source_origin | integer | Yes | Application code source (value is 1 for code repositories) |  
| source_dir | string | Yes | Build directory |  
| source_repo_auth_info | dict | Yes | Source repository authentication information |  

**Field Description for `source_repo_auth_info`:**  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| username | string | Yes | Username |  
| password | string | Yes | Password |  

**Field Description for `bkapp_spec`:**  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| build_config | dict | Yes | Build configuration |  

**Field Description for `build_config`:**  
| Field | Type | Required | Description |  
| ------ | ------ | ------ | ------ |  
| build_method | string | Yes | Build method (optional values: buildpack, dockerfile) |  

### Request Example  
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{   "is_plugin_app": false,   "code": "testappcode",   "name": "testappcode",   "source_config": {       "source_init_template": "dj2_with_auth",       "source_control_type": "bare_git",       "source_repo_url": "https://gitee.com/example/apps.git",       "source_origin": 1,       "source_dir": "plugin",       "source_repo_auth_info": {           "username": "xxxxxx ",           "password": "***"       }   },   "bkapp_spec": {       "build_config": {           "build_method": "buildpack"       }   }}' --insecure https://bkapi.example.com/api/bkpaas3/stag/bkapps/cloud-native/
```

### Response Example
```
{
    "application": {
        "id": "479ca05c-962a-43d2-bd2c-af7735f2ede1",
        "name": "testappcode",
        "modules": [
            {
                "name": "default",
                "is_default": true,
                "language": "Python"
            }
        ],
        "code": "testappcode",
        "name_en": "testappcode",
        "type": "cloud_native",
        "is_plugin_app": true,
        "is_ai_agent_app": true,
        "language": "Python",
        "is_active": true,
        "is_deleted": false,
        "last_deployed_date": null
    }
}
```

### Response Parameter Description

| Field                | Type     | Description                     |
|----------------------|----------|---------------------------------|
| id                   | string   | Application ID                  |
| name                 | string   | Application Name                |
| modules              | list     | Information about application modules |
| code                 | string   | Application Code                |
| name_en              | string   | Application English Name        |
| type                 | string   | Application Type                |
| is_plugin_app        | boolean  | Indicates whether it is a plugin application |
| is_ai_agent_app      | boolean  | Indicates whether it is an AI Agent tool |
| language             | string   | Application Language            |
| is_active            | boolean  | Indicates whether it is active   |
| is_deleted           | boolean  | Indicates whether it has been deleted |
| last_deployed_date   | string   | Last deployment date            |

#### Modules
| Field     | Type     | Description         |
|-----------|----------|---------------------|
| name      | string   | Module Name         |
| is_default | boolean  | Indicates whether it is the default module |
| language  | string   | Module Language      |
