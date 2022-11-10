### Resource Description

Query logs for a blue whale plug-in type app for internal system use only.

The interface retrieves all logs within the last 14 days by default, returning 200 logs at a time, and does not support customization for the time being.

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| private_token | string      | no  | Token allocated by PaaS platform, which must be provided when the app identity of the requester is not authenticated by PaaS platform |
| code | string |no| Location parameter, code of plug-in to be queried|
| scroll_id | string |no| Identification field for scrolling through pages|
| trace_id | string |yes| Identifier used to filter logs`trace_id`|


### Return result

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

### Return result description


|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|  scroll_id | str |Page turning identification field, which is passed in when obtaining the next page|
|  logs |list [objects] |List of log objects, sorted by creation time from new to old|
|  total | int |Total logs|

Note:

- page`logs` turning should be stopped when empty in response

`logs` Description of internal object fields:

|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|  plugin_code | str |Plug-in identifier|
|  environment | str |Deployment environment that generates logs,`stag` pre-release environment`prod`, production environment|
|  message | str |Log information|
|  detail | object |Structured log details|

**note**:`detail.json.trace_id` in the field, there is a highlight [bk highlight mark] ... [/bk front mark front] mark character, if required for front-end display `please handle it properly.