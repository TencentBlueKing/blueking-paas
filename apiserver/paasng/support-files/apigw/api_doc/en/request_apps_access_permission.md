### Resource Description
Internal interface, to one applicant (usually to the developer), and to apply for platform access rights of Tencent version and access rights of multiple applications at the same time. Currently, only applications on v3 platform are supported.

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| applicant_account   |  string |yes| Account number of permission applicant, which should be qq number|
| name | string |yes| Name of permission applicant|
| phone | string |yes| Cell phone number|
| email | string |yes| Email address|
| company | string |yes| Applicant's company|
| business | string |yes| Business|
| reason | string |yes| Reason for application|
| app_code_list | Array of strings | yes      | List of App IDs requesting access|


### Call example
```python
import json
import requests

# Filling parameters
data = {
  "applicant_account": "--",
  "name": "--",
  "phone": "--",
  "email": "--@qq.com",
  "company": "--",
  "app_code_list": [
    "app-id-1",
    "app-id-2"
  ],
  "business": "--",
  "reason": "--"
}

url = "http://bkapi.example.com/api/bkpaas3/prod/bkapps/access_control/multi_apply_record/"
PAAS_V3_TOKEN = "YOUR-ACCESS-TOKEN"
AUTHORIZATION = {'access_token': PAAS_V3_TOKEN}
headers = {'X-BKAPI-AUTHORIZATION': json.dumps(AUTHORIZATION)}

res = requests.post(url, headers=headers, json=data)
```

### Return result
```python
ret = res.json()
ret == [{
    "application": null,
    "status": "processing",
    "contacts": "BlueKing Assistant",
    "reason": "Platform permissions need to be manually reviewed"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "pass",
    "contacts": "rtx",
    "reason": "The bill drawer has the operational authority to apply, and the bill is automatically passed"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "processing",
    "contacts": "rtx",
    "reason": "The withdrawer does not have permission to operate the application, and needs to contact the developer of the application for review"
}, {
    "application": null,
    "status": "reject",
    "contacts": "rtx",
    "reason": "App does not exist"
}]
```

### Return result description
| Field | Type | Description                                |
|-------------|----------|----------------------------------------------------|
| application | Object   | The application for access is Null when applying for platform permission or when the application does not exist|
| status      |  string   | Enum: processing pass reject doc execution status     Processing: to be approved; PaaS: approved; Reject: reject    |
| contacts    |  string   | Contacts, separated by commas                                 |
| reason      |  string   | Cause                                               |


| Object annotation      | Field | Type                                       | Description |
|-------------|----------|----------------------------------------------------|--------------------|
| application | id       |  UUID                                               | Apply unique ID (UUID)|
|             | code     | string                                             | App id(code)    |
|             | name     | string                                             | App name    |