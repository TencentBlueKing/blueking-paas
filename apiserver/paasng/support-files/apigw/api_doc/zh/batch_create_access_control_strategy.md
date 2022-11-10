### 资源描述
对内接口, 用于给一个应用批量增加IP白名单,目前仅支持 v3 平台的应用

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 输入参数说明
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| content   | string | 是 | 申请的白名单策略内容, 如多条用;进行分割, IP支持掩码 |
| desc | string | 是 | 添加原因 | 
| path | string | 是 | 默认为*, 表示对所有路径生效，可以指定具体的URL路径前缀 |
| expires_at | string | 否 | 过期时间, 建议使用 isoformat 的日期, 即形如 yyyy-MM-dd HH:mm:ss |


### 调用示例
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

### 返回结果
<table class="model"><tbody><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 5096 -->added<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class=""><div class="markdown"><p>新增内容列表</p>
</div><span><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5111 -->minLength<!-- /react-text --><!-- react-text: 5112 -->: <!-- /react-text --><!-- react-text: 5113 -->1<!-- /react-text --></span></span></span></span></span></span></td></tr><tr class="false"><td style="vertical-align: top; padding-right: 0.2em; font-weight: bold;"><!-- react-text: 5117 -->ignored<!-- /react-text --><span style="color: red;">*</span></td><td style="vertical-align: top;"><span class="model"><span class=""><div class="markdown"><p>已存在被忽略的内容列表</p>
</div><span><span class="model"><span class="prop"><span class="prop-type">string</span><span style="color: rgb(107, 107, 107); font-style: italic;"><br><!-- react-text: 5148 -->minLength<!-- /react-text --><!-- react-text: 5149 -->: <!-- /react-text --><!-- react-text: 5150 -->1<!-- /react-text --></span></span></span></span></span></span></td></tr><tr>&nbsp;</tr></tbody></table>