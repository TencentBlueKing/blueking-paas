### 功能描述

以应用身份、代表指定用户为 AI Agent 应用申请 AccessToken。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

调用方需要提供用户在开发者中心的登录凭证（bk_ticket / bk_token），放在请求头里，平台会用该凭证换出用户身份。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| env_name | string | 是 | 环境，可选值 "test" / "prod" |

#### 2、请求头

两个请求头二选一，传哪个取决于平台使用的鉴权方式。

| 请求头 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| X-USER-BK-TICKET | string | 二选一 | 用户的 bk_ticket，平台使用 bk_ticket 鉴权时传这个 |
| X-USER-BK-TOKEN | string | 二选一 | 用户的 bk_token，平台使用 bk_token 鉴权时传这个 |

凭证类型必须与平台的鉴权后端一致，另一种凭证的请求头会被忽略。多租户环境下平台只能使用 bk_token。

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-USER-BK-TICKET: {{your bk_ticket}}' --insecure 'https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/oauth/token/prod/'
```

### 返回结果示例

```json
{
    "access_token": "--",
    "refresh_token": "--",
    "expires_in": 604784
}
```

### 返回结果参数说明

| 参数名称 | 参数类型 | 参数说明 |
| -------- | -------- | -------- |
| access_token | string | 具有应用身份认证的 AccessToken |
| refresh_token | string | 用于调用 refresh app token 接口 |
| expires_in | int | 有效时间，由上游签发服务决定 |
