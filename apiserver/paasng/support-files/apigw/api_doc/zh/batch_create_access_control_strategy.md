### 功能描述
对内接口，用于给一个应用批量增加IP白名单，目前仅支持v3平台的应用。


### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称   | 参数类型 | 必须 | 参数说明                                   |
| ---------- | -------- | ---- | ------------------------------------------ |
| content    | string   | 是   | 申请的白名单策略内容，如多条用;进行分割，IP支持掩码 |
| desc       | string   | 是   | 添加原因                                   |
| path       | string   | 是   | 默认为*，表示对所有路径生效，可以指定具体的URL路径前缀 |
| expires_at | string   | 否   | 过期时间，建议使用 isoformat 的日期，即形如 yyyy-MM-dd HH:mm:ss |

### 请求示例
```python
import json
import requests

# 填充参数
data = {
  "content": ";".join(["your", "ip", "list"]),
  "desc": "sth",
  "path": "*",
  "expires_at": None
}

# app_code: 按需填写
# restriction_type: 选填 user|ip
url = "http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/access_control/restriction_type/{restriction_type}/strategy/"

YOUR_PAAS_V3_TOKEN = "--"
AUTHORIZATION = {'access_token': YOUR_PAAS_V3_TOKEN}
headers = {'X-BKAPI-AUTHORIZATION': json.dumps(AUTHORIZATION)}

res = requests.post(url, headers=headers, json=data)
assert res.status_code == 201
```

### 返回结果示例
```json
{
  "added": [],
  "ignored": []
}
```

### 返回结果参数说明

| 字段    | 类型   | 是否必填 | 描述                 |
| ------- | ------ | -------- | -------------------- |
| added   | string | 是       | 新增内容列表         |
| ignored | string | 是       | 已存在被忽略的内容列表 |