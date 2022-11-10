### Resource Description

Create light app information for management APP only.

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

| Field | Type | Required | Description                                          |
| ------------ | -------- | ---- | ------------------------------------------------------------ |
| app_code     |  string   | yes | APP Code of parent app                                            |
| app_name     |  string   | yes | Light app name                                                |
| app_url      |  string   | yes | App link                                                     |
| developers   |  array    | yes      | List of app developer usernames                                         |
| app_tag      |  string   | yes      | App classification, optional classification: "OpsTools,""MonitorAlarm,""ConfManage,""DevTools,""enterprise IT,""Office app,""Other". Use 'Other' if you pass in an empty parameter or if it is not an appeal classification |
| creator      |  string   | yes      | Creator                                                       |
| logo         |  string   | no | Icon png file base64 encode form                                |
| introduction | string   | no | Introduction to apps                                                   |
| width        |  int      | no | The width of the open window of the app on the desktop, which defaults to the width of the parent app                     |
| height       |  int      | no | Height of open window of app on desktop, default is parent app height                     |

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
| state        |  int    | App status        |