### Feature Description

Query the standard output logs of the application.

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID, e.g. "monitor" |
| module   | string | Yes | Module name, e.g. "default" |

#### 2. Interface Parameters:

| Parameter Name | Type | Required | Description |
|------|------| :------: |-------------|
| end_time | string | No | End time |
| log_type | string | No | Log type |
| scroll_id | string | No | Scroll ID |
| start_time | string | No | Start time |
| time_range | string | Yes | Time range |

### Request Example

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### Response Result Example

```json
{
  "result": true,
  "data": {
    "scroll_id": "12345",
    "logs": [
      {
        "timestamp": "2021-08-30T10:00:00Z",
        "log_type": "stdout",
        "message": "Application started"
      },
      {
        "timestamp": "2021-08-30T10:01:00Z",
        "log_type": "stdout",
        "message": "Request received"
      }
    ]
  }
}
```

### Response Result Parameter Description

| Field | Type | Description |
| ------ | ------ | ------ |
| result | bool | Request result, true for success, false for failure |
| data | dict | Returned data |

data
| Field | Type | Description |
| ------ | ------ | ------ |
| scroll_id | string | Scroll ID |
| logs | list | Log list |

logs
| Field | Type | Description |
| ------ | ------ | ------ |
| timestamp | string | Log timestamp |
| log_type | string | Log type |
| message | string | Log message |