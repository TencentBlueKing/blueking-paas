### Resource Description

Internal interface, which is used to add IP white list to an app in batches. Currently, it only supports apps on v3 platform

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| content   |  string |yes| The content of the white list strategy applied for, such as multiple items; Split, IP support mask|
| desc | string |yes| Add reason|
| path | string |yes| The default value is *, which means it is effective for all paths, and a specific URL path prefix can be specified|
| expires_at | string |no| Expiration time, it is recommended to use the date of isoformat, i.e., In the form of yyy m dd HH: mm:ss|


### Call example
```python
import json
import requests

# Fill Parameters
data = {
  "content": ";".join(["your", "ip", "list"]),
  "desc": "sth",
  "path": "*",
  "expires_at": None
}

# app_code: Fill in as required
# restriction_type: Optional user|ip
url = "http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/access_control/restriction_type/{restriction_type}/strategy/"

YOUR_PAAS_V3_TOKEN = "--"
AUTHORIZATION = {'access_token': YOUR_PAAS_V3_TOKEN}
headers = {'X-BKAPI-AUTHORIZATION': json.dumps(AUTHORIZATION)}

res = requests.post(url, headers=headers, json=data)
assert res.status_code == 201
```

### Return result

|   added*   | New content list<br/>stringminLength: 1 |
| ------------ | ------------ |
| **ignored*** | **There is already a list of ignored content<br/>stringminLength: 1**	|

