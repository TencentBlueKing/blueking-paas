### Description
Create light application information.

Note: By default, only standard operation (app ID: bk_sops) is allowed to call the APIs related to light apps, if you need to call them, please contact the platform administrator to add permissions.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name  | Parameter Type | Required | Parameter Description                                                                                   |
| --------------  | -------------- | -------- | -------------------------------------------------------------------------------------------------------- |
| parent_app_code | string         | Yes      | Parent application's APP Code                                                                            |
| app_name        | string         | Yes      | Light application name                                                                                   |
| app_url         | string         | Yes      | Application link                                                                                         |
| developers      | array          | Yes      | Application developer username list                                                                      |
| creator         | string         | Yes      | Creator                                                                                                  |
| app_tag         | string         | No      | Application category, optional categories: "OpsTools" (Operation Tools), "MonitorAlarm" (Monitoring and Alarm), "ConfManage" (Configuration Management), "DevTools" (Development Tools), "EnterpriseIT" (Enterprise IT), "OfficeApp" (Office Applications), "Other" (Others). If an empty parameter or not one of the above categories is passed, use "Other" |
| logo            | string         | No       | Icon png file in base64 encoding format                                                                  |
| introduction    | string         | No       | Application introduction                                                                                 |
| width           | int            | No       | Application window width when opened on the desktop, default to parent application width                |
| height          | int            | No       | Application window height when opened on the desktop, default to parent application height              |
| app_tenant_mode | string | No     |When creating lightweight apps under the operation tenant, users can choose: `global` (all tenants) or `single` (single tenant). Default is single tenant if not specified.|
### Request Example

```
curl -X POST -H 'X-Bkapi-Authorization: {"bk_app_code": "appid", "bk_app_secret": "***"}' -d '{ "parent_app_code": "bksops", "app_name":"name" "app_url": "http://example.com", "developers": ["admin"], "creator: "admin" }' --insecure http://bkapi.example.com/api/bkpaas3/prod/system/light-applications
```

### Response Result Example

```json
{
  "bk_error_msg": "",
  "bk_error_code": 0,
  "data": {
        "light_app_code": "demo_code",
        "app_name": "name",
        "app_url": "http://example.com",
        "introduction": "-",
        "creator": "admin",
        "logo": "",
        "developers": [
            "admin"
        ],
        "state": 4
  },
  "result": true
}
```

### Response Result Parameter Description

| Name          | Type   | Description          |
| ------------- | ------ | -------------------- |
| light_app_code      | string | Light application's APP Code |
| app_name      | string | Light application's name      |
| app_url       | string | Application link          |
| introduction  | string | Application introduction          |
| creator       | string | Creator            |
| logo          | string | Icon address          |
| developers    | array  | Developer list        |
| state         | int    | Application status          |