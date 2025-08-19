### 功能描述
对内接口，用于给一个申请人（一般是给开发商）同时申请Tencent版平台访问权限以及多个应用的访问权限。目前仅支持v3平台的应用。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称          | 参数类型        | 是否必填 | 参数说明                   |
| ----------------- | --------------- | -------- | -------------------------- |
| applicant_account | string          | 是       | 权限申请人账号，应为QQ号    |
| name              | string          | 是       | 权限申请人姓名             |
| phone             | string          | 是       | 手机号码                   |
| email             | string          | 是       | 邮箱地址                   |
| company           | string          | 是       | 申请人所在公司             |
| business          | string          | 是       | 所属业务                   |
| reason            | string          | 是       | 申请原因                   |
| app_code_list     | Array of strings | 是       | 申请访问的应用ID列表       |

### 请求示例
```python
import json
import requests

# 填充参数
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

### 返回结果示例
```python
ret = res.json()
ret == [{
    "application": null,
    "status": "processing",
    "contacts": "蓝鲸助手",
    "reason": "平台权限需人工审核"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "pass",
    "contacts": "rtx",
    "reason": "提单人具有应用的操作权限，单据自动通过"
}, {
    "application": {
        "id": "--",
        "code": "--",
        "name": "--"
    },
    "status": "processing",
    "contacts": "rtx",
    "reason": "提单人不具有该应用的操作权限, 需联系该应用的开发者进行审核"
}, {
    "application": null,
    "status": "reject",
    "contacts": "rtx",
    "reason": "应用不存在"
}]
```

### 返回结果参数说明
| 参数名称    | 参数类型 | 参数说明                                           |
|-------------|----------|----------------------------------------------------|
| application | Object   | 申请访问的应用, 申请平台权限时或应用不存在时为Null |
| status      | string   | Enum: "processing" "pass" "reject" 单据执行状态     processing: 待审核; paas: 审核通过; reject: 拒绝    |
| contacts    | string   | 联系人, 以逗号分隔                                 |
| reason      | string   | 原因                                               |

#### application
| 参数名称 | 参数类型 | 参数说明           |
|----------|----------|--------------------|
| id       | UUID     | 应用唯一标志(UUID) |
| code     | string   | 应用ID(code)       |
| name     | string   | 应用名称           |