### Description
Query basic information of multi-platform applications based on id or name fuzzy search. Only the first 1000 pieces of data will be returned, with priority given to applications on PaaS3.0 Developer Center.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description             |
|----------------|----------------|----------|------------------------------------|
| keyword        | string         | No       | Application ID, application name, fuzzy query |
| limit          | int            | No       | Default value is 100, maximum value is 100 |
| offset         | int            | No       | Default value is 0, maximum value is 900 |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/list/minimal/
```

### Response Result Example
```javascript
{
    "count": 3,
    "next": null,
    "previous": null,
    "results": [
        {
            "code": "myapp",
            "name": "myapp"
        },
        {
            "code": "myapp2d",
            "name": "myappdfd"
        }
    ]
}
```

### Response Result Parameter Description
| Parameter Name   | Parameter Type | Parameter Description             |
|------------------|----------------|------------------------------------|
| count            | int            | Total number of applications |
| next             | string/null    | Next page link, if none, then null |
| previous         | string/null    | Previous page link, if none, then null |
| results          | array          | Application information list |
| results.code     | string         | Application ID |
| results.name     | string         | Application name |