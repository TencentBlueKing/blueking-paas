### 资源描述
获取代表指定应用和用户身份的 AccessToken

### 输入参数说明
|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   api_gateway_env | string |  是 | 环境，可选值 "test" / "prod" / "lesscode" |
| X-USER-BK-TICKET | string | 是 | 用户的 bk_ticket |

### 调用示例

```bash
curl -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{填写你的 AccessToken}}"}' -H 'X-USER-BK-TICKET: {{你的 bk_ticket }}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{填写你的AppCode}}/oauth/token/{{api_gateway_env}}/ -H "COOKIE: bk_uid={{你的 RTX}}&bk_ticket={{你的bk_ticket}}"
```

### 返回结果
```json
{
  "message": "",
  "code": "0",
  "data": {
    "access_token": "--",
    "refresh_token": "--",
    "expires_in": 604784,
  },
  "result": true
}
```

### 返回结果说明
|   参数名称   |  参数类型  |           参数说明             |
| ------------ | ---------- | ------------------------------ |
|  access_token  | string |  具有应用身份认证的 AccessToken |
|  refresh_token  | string |  用于调用 refresh app token 接口 |
|  expires_in |int| 有效时间， lesscode 环境默认有效期为7天 |