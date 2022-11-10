### Resource Description

Query the list of applications that the specified user has permission, which is only used by internal system

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description
| Field | Type | Required | Description                |
|---------------|--------------|-----|--------------------------------|
| private_token | string       | no | Token allocated by PaaS platform, which must be provided when the app identity of requester is not authenticated by PaaS platform |
| username      | string | yes   | username |

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
    }
]
```

### Return result description

- Archived apps do not return
