### Resource Description
A brief description of the registered resource

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID (app id), you can get it from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |
| app_secret | string |no| The security key (app secret) can be obtained from BlueKing Developer Center -> App Basic Settings -> Basic Information -> Authentication Information |

### Call example
```python
from bkapigw.paasv3.shortcuts import get_client_by_request
client = get_client_by_request(request)
# Fill Parameters
kwargs = {

}
result = client.api.api_test(kwargs)
```

### Return result
```json
# Internal version
{
    "credentials": {
        "GCS_MYSQL_HOST": "--",
        "GCS_MYSQL_PORT": --,
        "GCS_MYSQL_NAME": "--",
        "GCS_MYSQL_USER": "--",
        "GCS_MYSQL_PASSWORD": "--"
    }
}

# Enterprise version
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}

# Failure to return
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "Failed to read Enhanced Service Instance information: No valid configuration information could be retrieved."
}

```

### Return result description
|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|              |            |                                |