### Feature Description
Query the logs of a "BlueKing Plugin" type application for internal system use only. This interface defaults to searching all logs within the last 14 days, returning 200 logs each time, and does not support customization.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | No       | Positional parameter, the code of the plugin to be queried |

#### 2. Interface Parameters:
| Field     | Type   | Required | Description                                  |
| --------- | ------ | -------- | -------------------------------------------- |
| scroll_id | string | No       | Identifier field for scroll pagination       |
| trace_id  | string | Yes      | `trace_id` identifier for filtering logs     |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/appid1/logs/?trace_id=1111'
```

### Response Result Example
```javascript
{
    "scroll_id": "FGluY2x1Z...",
    "logs": [
        {
            "plugin_code": "bk-plugin-demo",
            "environment": "stag",
            "process_id": "web",
            "stream": "component",
            "message": "A log message",
            "detail": {
                "json.asctime": "2021-08-26 11:06:44,325",
                "json.funcName": "foo_function",
                "json.levelname": "INFO",
                "json.lineno": 16,
                "json.message": "A log message",
                "json.pathname": "/app/foo.py",
                "json.process": 30,
                "json.thread": 140625517852824,
                "json.trace_id": "[bk-mark]2c1f0c1ae2c84505b1ed14ad8e924a12[/bk-mark]"
            },
            "ts": "2021-08-26 11:06:44"
        }
    ],
    "total": 1
}
```

### Response Result Parameter Description
| Parameter Name | Parameter Type | Parameter Description                          |
| -------------- | -------------- | ---------------------------------------------- |
| scroll_id      | str            | Pagination identifier, pass this value to get the next page |
| logs           | list[objects]  | List of log objects, sorted by creation time from newest to oldest |
| total          | int            | Total number of logs                           |

`logs` object field description:

| Parameter Name | Parameter Type | Parameter Description                          |
| -------------- | -------------- | ---------------------------------------------- |
| plugin_code    | str            | Plugin identifier                             |
| environment    | str            | Deployment environment where the log was generated, `stag` -> Pre-release environment, `prod` -> Production environment |
| message        | str            | Log message                                   |
| detail         | object         | Structured log details                         |

**Note**: In the `detail.json.trace_id` field, there are `[bk-mark]...[/bk-mark]` marker characters for highlighting fields. If used for frontend display, please handle them properly.