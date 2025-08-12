### Function Description
Internal interface for adding IP whitelist in bulk to an application, currently only supports v3 platform applications.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| content        | string         | Yes      | Applied whitelist policy content, separated by semicolons for multiple entries, IP supports mask |
| desc           | string         | Yes      | Reason for adding     |
| path           | string         | Yes      | Default is *, which means it takes effect on all paths, or you can specify a specific URL path prefix |
| expires_at     | string         | No       | Expiration time, it is recommended to use isoformat date, in the form of yyyy-MM-dd HH:mm:ss |

### Request Example
```python
import json
import requests

# Fill in the parameters
data = {
  "content": ";".join(["your", "ip", "list"]),
  "desc": "sth",
  "path": "*",
  "expires_at": None
}

# app_code: Fill as needed
# restriction_type: Optional user|ip
url = "http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/access_control/restriction_type/{restriction_type}/strategy/"

YOUR_PAAS_V3_TOKEN = "--"
AUTHORIZATION = {'access_token': YOUR_PAAS_V3_TOKEN}
headers = {'X-BKAPI-AUTHORIZATION': json.dumps(AUTHORIZATION)}

res = requests.post(url, headers=headers, json=data)
assert res.status_code == 201
```

### Response Result Example
```json
{
  "added": ["your", "ip", "list"],
  "ignored": []
}
```

### Response Result Parameter Description

| Field   | Type   | Required | Description             |
| ------- | ------ | -------- | ----------------------- |
| added   | string | Yes      | List of added content   |
| ignored | string | Yes      | List of ignored content |