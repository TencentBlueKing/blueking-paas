### Feature Description
Create light application information, for management-side APP use only.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description                                                                                   |
| -------------- | -------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| app_code       | string         | Yes      | Parent application's APP Code                                                                            |
| app_name       | string         | Yes      | Light application name                                                                                   |
| app_url        | string         | Yes      | Application link                                                                                         |
| developers     | array          | Yes      | Application developer username list                                                                      |
| app_tag        | string         | Yes      | Application category, optional categories: "OpsTools" (Operation Tools), "MonitorAlarm" (Monitoring and Alarm), "ConfManage" (Configuration Management), "DevTools" (Development Tools), "EnterpriseIT" (Enterprise IT), "OfficeApp" (Office Applications), "Other" (Others). If an empty parameter or not one of the above categories is passed, use "Other" |
| creator        | string         | Yes      | Creator                                                                                                  |
| logo           | string         | No       | Icon png file in base64 encoding format                                                                  |
| introduction   | string         | No       | Application introduction                                                                                 |
| width          | int            | No       | Application window width when opened on the desktop, default to parent application width                |
| height         | int            | No       | Application window height when opened on the desktop, default to parent application height              |

### Request Example

```
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "appid", "bk_app_secret": "***"}' -d '{ "parent_app_code": "bksops", "app_url": "http://example.com", "developers": "admin", "creator: "admin" }' --insecure http://bkapi.example.com/api/bkpaas3/prod/system/light-applications
```

### Response Result Example

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
    "app_code": "demo-0727-001_ps",
    "app_name": "demo-0727-001_ps",
    "app_url": "http://app.demo.com",
    "introduction": "Test application",
    "creator": "admin",
    "logo": "http://demo.com/app-logo/o_demo-0727-001_ps.png",
    "developers": [
      "admin"
    ]
  },
  "result": true
}
```

### Response Result Parameter Description

| Name          | Type   | Description          |
| ------------- | ------ | -------------------- |
| app_code      | string | Light application's APP Code |
| app_name      | string | Light application's name      |
| app_url       | string | Application link          |
| introduction  | string | Application introduction          |
| creator       | string | Creator            |
| logo          | string | Icon address          |
| developers    | array  | Developer list        |
| state         | int    | Application status          |