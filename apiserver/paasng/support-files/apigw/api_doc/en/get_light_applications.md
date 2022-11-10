### Resource Description

Obtain light app information, which is only used by the management side app.

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
    "app_code": "demo-0727-001_ps",
    "app_name": "demo-0727-001_ps",
    "app_url": "http://app.demo.com",
    "introduction": "Test App",
    "creator": "admin",
    "logo": "http://demo.com/app-logo/o_demo-0727-001_ps.png",
    "developers": [
      "admin"
    ]
  },
  "result": true
}
```

### Return result description

| Name         | Type   | Description              |
| ------------ | ------ | ----------------- |
| app_code     |  string |APP Code for light apps|
| app_name     |  string |Name of light app      |
| app_url      |  string |App link          |
| introduction | string |App introduction          |
| creator      |  string |Creator            |
| logo         |  string |Icon address          |
| developers   |  array  |List of developers        |
| state        |  int    | App status          |