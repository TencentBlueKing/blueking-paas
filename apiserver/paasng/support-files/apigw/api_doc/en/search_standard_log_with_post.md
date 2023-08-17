### Feature Description

Query application standard output logs.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID, such as "monitor" |
| module         | string         | Yes      | Module name, such as "default" |

#### 2. Interface Parameters:

| Parameter Name | Parameter Location | Type                              | Required | Description |
| -------------- | ------------------ | --------------------------------- | -------- | ----------- |
| end_time       | `query`            | string                            | No       |             |
| log_type       | `query`            | string                            | No       |             |
| scroll_id      | `query`            | string                            | No       |             |
| start_time     | `query`            | string                            | No       |             |
| time_range     | `query`            | string                            | Yes      |             |
| data           | `body`             | SearchStandardLogWithPostBody     | Yes      |             |

data
| Field  | Type                              | Required | Description |
| ------ | --------------------------------- | -------- | ----------- |
| query  | SearchStandardLogWithPostParamsBodyQuery | Yes       |             |
| sort   | interface{}                       | No       | Sort, e.g., {'response_time': 'desc', 'other': 'asc'} |

### Request Example

```bash
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/log/standard_output/list/?time_range=1h'
```

### Response Result Example

```json
{
  "code": 200,
  "data": {
    "logs": [
      {
        "environment": "prod",
        "message": "log message",
        "pod_name": "app-1",
        "process_id": "123",
        "timestamp": "2021-01-01T00:00:00Z"
      }
    ],
    "scroll_id": "scroll_id",
    "total": 1
  }
}
```

### Response Result Parameter Description

| Field          | Type                                            | Required | Description       |
| -------------- | ----------------------------------------------- | -------- | ----------------- |
| code           | integer                                         | Yes      | Status code       |
| data           | SearchStandardLogWithPostOKBodyData             | Yes      | Returned data     |
| data.logs      | []SearchStandardLogWithPostOKBodyDataLogsItems0 | Yes      | Log list          |
| data.scroll_id | string                                          | Yes      | ES scroll_id for pagination |
| data.total     | integer                                         | Yes      | Log count         |