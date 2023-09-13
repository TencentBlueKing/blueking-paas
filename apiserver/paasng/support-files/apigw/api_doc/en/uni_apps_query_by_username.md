### Description
Query the list of applications that the specified user has permission to access, for internal system use only.

### Request Parameters

#### 1. Path Parameters:
None

#### 2. API Parameters:
| Parameter Name | Type | Required | Description |
| -------------- | ---- | -------- | ----------- |
| username       | string | Yes | Username |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/query/by_username/?username=admin
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
    }
]
```

### Response Result Parameter Description
| Parameter Name | Type | Description |
| -------------- | ---- | ----------- |
| source         | int  | Source      |
| name           | string | Application Name |
| code           | string | Application Code |
| region         | string | Region      |
| logo_url       | string | Application Logo URL |
| developers     | list | Developer List |
| creator        | string | Creator     |
| created        | string | Creation Time |

**Note: Applications that have been removed from the shelves will not be returned**