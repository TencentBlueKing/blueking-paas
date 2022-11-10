### Resource Description

Query app basic information according to app ID, which is only used by internal system

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description
| Field | Type | Required | Description                |
|---------------|--------------|-----|--------------------------------|
| private_token | string       | no | Token allocated by PaaS platform, which must be provided when the app identity of requester is not authenticated by PaaS platform |
| id            | List [string] |yes   | Comma-separated list of app IDs|

### Return result

```javascript
[
    {
        "source": 1,
        "name": "Batman",
        "code": "batman",
        "logo_url": "http://example.com/app-logo/blueking_app_default.png",
        "developers": [
            "username",
        ],
        "creator": "username",
        "created": "2019-08-13 19:15:38",
		"contact_info": {
		    // Recent Operators
            "latest_operator": "username",
			// People deployed in the last 1 month, in no particular order
            "recent_deployment_operators": [
                "username"
            ]
        }
    }
]
```

### Return result description

- The contents of the result list are in the same order as the AppID of the request parameters
- When an App ID can not find any information, the location content is null

| Field | Type | Description      |
|----------|----------|----------------------|
| source   | App source platform | 1 default (v3), 2 old version|