### Description
Query the logs of a "BlueKing Plugin" type application for internal system use only. This interface defaults to searching all logs within the last 14 days, returning 200 logs each time, and does not support customization.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | Yes       | Positional parameter, the code of the plugin to be queried |

#### 2. API Parameters:
| Field     | Type   | Required | Description                                  |
| --------- | ------ | -------- | -------------------------------------------- |
| scroll_id | string | No       | Identifier field for scroll pagination       |
| trace_id  | string | Yes      | `trace_id` identifier for filtering logs     |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugins/appid1/logs/?trace_id=1111'
```

### Response Result 
#### Success Response
```javascript
{
    "logs": [
        {
            "timestamp": 1724152930,
            "message": "[execute] plugin execute failed",
            "raw": {
                "otelServiceName": null,
                "pathname": "/app/.heroku/python/lib/python3.6/site-packages/bk_plugin_framework/runtime/executor.py",
                "otelTraceID": null,
                "otelSpanID": null,
                "message": "[execute] plugin execute failed",
                "__ext_json.lineno": 99,
                "__ext_json.process": 6368,
                "__ext_json.thread": 139939413554944,
                "__ext_json.trace_id": "88d9254695094eb09851f261cda8d5e6",
                "__ext_json.exc_info": "Traceback (most recent call last):\n  File ...",
                "funcName": "execute",
                "levelname": "ERROR",
                "region": "ieod",
                "app_code": "bkchat-sops",
                "module_name": "default",
                "environment": "prod",
                "process_id": "web",
                "pod_name": "bkapp-bkchat-sops-prod--web-865dddfdcc-fxg8p",
                "stream": null,
                "ts": "2024-08-20 19:22:10",
                "json.levelname": "ERROR",
                "json.funcName": "execute",
                "json.message": "[execute] plugin execute failed"
            },
            "detail": {
                "otelServiceName": null,
                "pathname": "/app/.heroku/python/lib/python3.6/site-packages/bk_plugin_framework/runtime/executor.py",
                "otelTraceID": null,
                "otelSpanID": null,
                "message": "[execute] plugin execute failed",
                "__ext_json.lineno": 99,
                "__ext_json.process": 6368,
                "__ext_json.thread": 139939413554944,
                "__ext_json.trace_id": "88d9254695094eb09851f261cda8d5e6",
                "__ext_json.exc_info": "Traceback (most recent call last):\n ...",
                "funcName": "execute",
                "levelname": "ERROR",
                "region": "ieod",
                "app_code": "bkchat-sops",
                "module_name": "default",
                "environment": "prod",
                "process_id": "web",
                "pod_name": "bkapp-bkchat-sops-prod--web-865dddfdcc-fxg8p",
                "stream": null,
                "ts": "2024-08-20 19:22:10",
                "json.levelname": "ERROR",
                "json.funcName": "execute",
                "json.message": "[execute] plugin execute failed"
            },
            "plugin_code": "bkchat-sops",
            "environment": "prod",
            "process_id": "web",
            "stream": "<object object at 0x7f144e63a540>",
            "ts": "2024-08-20 19:22:10"
        }
    ],
    "total": 11,
    "dsl": "{\"query\": {\"bool\": {\"filter\": ...",
    "scroll_id": "FGluY2x1ZGVfY29udG..."
}
```

#### Exception Response
```
{
    "code": "VALIDATION_ERROR",
    "detail": "trace_id: 该字段是必填项。",
    "fields_detail": {
        "trace_id": [
            "该字段是必填项。"
        ]
    }
}
```

### Response Result Parameter Description
| Parameter Name | Parameter Type | Parameter Description                          |
| -------------- | -------------- | ---------------------------------------------- |
| scroll_id      | str            | Pagination identifier, pass this value to get the next page |
| logs           | list[objects]  | List of log objects, sorted by creation time from newest to oldest |
| total          | int            | Total number of logs                           |
| dsl            | string         | DSL query                                      |

`logs` object field description:

| Parameter Name | Parameter Type | Parameter Description                          |
| -------------- | -------------- | ---------------------------------------------- |
| plugin_code    | str            | Plugin identifier                              |
| environment    | str            | Deployment environment where the log was generated, `stag` -> Pre-release environment, `prod` -> Production environment |
| message        | str            | Log message                                    |
| raw            | object         | Raw log                                        |
| detail         | object         | Structured log details                         |
| process_id     | string         | Process unique type                            |
| stream         | string         | Stream                                         |
| ts             | string         | Timestamp                                      |

**Note**: In the `detail.json.trace_id` field, there are `[bk-mark]...[/bk-mark]` marker characters for highlighting fields. If used for frontend display, please handle them properly.