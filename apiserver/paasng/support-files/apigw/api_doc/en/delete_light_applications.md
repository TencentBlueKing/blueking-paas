### Resource Description

Delete the light APP for use only by the management app.

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

| Field | Type | Required | Description |
| -------- | -------- | ---- | ----------------- |
| app_code | string   | yes | APP Code for light apps|

### Return result

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "count": 1
  },
  "result": true
}
```

### Return result description

| Name         | Type   | Description              |
| ------------ | ------ | ----------------- |
| count     |  int |Number of apps deleted|