### Description
Obtain the database connection information for the specified application, module, and environment.

Note: By default, only Blueking lesscode development platform (app ID: bk_lesscode) is allowed to call this API, if you need to call it, please contact the platform administrator to add permissions.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name           |
| env            | string         | Yes      | Environment, e.g. "prod" |

#### 2. API Parameters:
None.

### Request Example
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "appid1", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/modules/default/envs/prod/lesscode/query_db_credentials
```

### Response Result Example

#### Success Response
```json
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}
```
| Parameter Name               | Parameter Type | Parameter Description          |
| -----------------------------| -------------- | ------------------------------ |
| credentials                  | dict           | Database connection information|
| credentials.MYSQL_HOST       | string         | Database host address          |
| credentials.MYSQL_PORT       | int            | Database port                  |
| credentials.MYSQL_NAME       | string         | Database name                  |
| credentials.MYSQL_USER       | string         | Database username              |
| credentials.MYSQL_PASSWORD   | string         | Database password              |

#### Failure response
```
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "Failed to read enhanced service instance information: Unable to obtain valid configuration information."
}

```

| Parameter Name   | Parameter Type | Parameter Description          |
| -----------------| -------------- | ------------------------------ |
| code             | string         | Error code                     |
| detail           | string         | Error details                  |