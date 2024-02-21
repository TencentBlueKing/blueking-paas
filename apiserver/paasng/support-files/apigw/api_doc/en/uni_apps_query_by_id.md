### Description

Query application basic information based on the application ID, for internal system use only.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| id             | List[string]   | Yes      | Comma-separated list of application IDs (bk_app_code) |
| include_inactive_apps        | boolean   | No       | Whether to query inactive applications, the default value is False |
| include_developers_info        | boolean   | No      | Whether to query developer info, the default is True. This option may extend API response time; disable to improve efficiency if not required. |

### Request Example

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/query/by_id/?id={bk_app_code}'
```

### Response Result Example

```javascript
[
    {
        "source": 1,
        "name": "Batman",
        "code": "batman",
        "region": "default",
        "logo_url": "http://example.com/app-logo/blueking_app_default.png",
        "developers": [
            "username",
        ],
        "creator": "username",
        "created": "2019-08-13 19:15:38",
		"contact_info": {
		    // Latest operator
            "latest_operator": "username",
			// People who have deployed in the last 1 month, ranking is not in order
            "recent_deployment_operators": [
                "username"
            ]
        }
    }
]
```

### Response Result Parameter Description

- The content in the result list is consistent with the order of AppID in the request parameters.
- When no information can be found for a certain application ID, the content at that position is null.

| Parameter Name | Parameter Type | Parameter Description |
| -------------- | -------------- | --------------------- |
| source         | int            | Application source platform, 1 - Default (v3), 2 - Old version |
| name           | string         | Application name |
| code           | string         | Application code |
| region         | string         | Application region, default is "default" |
| logo_url       | string         | Application Logo URL |
| developers     | List[string]   | List of application developers |
| creator        | string         | Application creator |
| created        | string         | Application creation time |
| contact_info   | dict           | Contact information |
| contact_info.latest_operator | string | Latest operator |
| contact_info.recent_deployment_operators | List[string] | People who have deployed in the last 1 month, ranking is not in order |