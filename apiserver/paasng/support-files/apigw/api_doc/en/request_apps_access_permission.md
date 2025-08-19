### Description
Internal interface for granting a requester (usually a developer) access to the Tencent platform and multiple applications at the same time. Currently, only v3 platform applications are supported.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name     | Parameter Type   | Required | Parameter Description        |
| ------------------ | ---------------- | -------- | ---------------------------- |
| applicant_account  | string           | Yes      | Requester's account, should be QQ number |
| name               | string           | Yes      | Requester's name             |
| phone              | string           | Yes      | Phone number                 |
| email              | string           | Yes      | Email address                |
| company            | string           | Yes      | Requester's company          |
| business           | string           | Yes      | Related business             |
| reason             | string           | Yes      | Reason for application        |
| app_code_list      | Array of strings | Yes      | List of application IDs to be accessed |

### Request Example
```python
import json
import requests

# Fill in parameters
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

### Response Result Example
```python
ret = res.json()
ret == [{
    "application": null,
    "status": "processing",
    "contacts": "Blue Whale Assistant",
    "reason": "Platform permissions require manual review"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "pass",
    "contacts": "rtx",
    "reason": "The submitter has the operation permission of the application, and the document is automatically approved"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "processing",
    "contacts": "rtx",
    "reason": "The submitter does not have the operation permission of the application and needs to contact the developer of the application for review"
}, {
    "application": null,
    "status": "reject",
    "contacts": "rtx",
    "reason": "Application does not exist"
}]
```

### Response Result Parameter Description
| Parameter Name | Parameter Type | Parameter Description                                           |
| -------------- | -------------- | --------------------------------------------------------------- |
| application    | Object         | Application to be accessed, Null when applying for platform permissions or when the application does not exist |
| status         | string         | Enum: "processing" "pass" "reject" Document execution status: processing: Pending review; pass: Approved; reject: Rejected |
| contacts       | string         | Contacts, separated by commas                                   |
| reason         | string         | Reason                                                          |

#### application
| Parameter Name | Parameter Type | Parameter Description |
| -------------- | -------------- | --------------------- |
| id             | UUID           | Application unique identifier (UUID) |
| code           | string         | Application ID (code) |
| name           | string         | Application name      |