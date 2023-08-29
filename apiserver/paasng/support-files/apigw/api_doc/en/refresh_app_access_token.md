### Description
Refresh the AccessToken representing the specified application and user identity.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID |
| api_gateway_env | string | Yes | Environment, optional values "test" / "prod" / "lesscode" |
| X-USER-BK-TICKET | string | Yes | User's bk_ticket |

### Request Example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Enter your AccessToken}}"}' -H 'X-USER-BK-TICKET: {{Your bk_ticket }}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Enter your AppCode}}/oauth/token/{{api_gateway_env}}/refresh -H "COOKIE: bk_uid={{Your RTX}}&bk_ticket={{Your bk_ticket}}" -H "accept: application/json" -d "{ \"refresh_token\": \"{Your refresh_token}\"}"
```

### Response Result Example

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

### Response Result Parameter Description

| Parameter Name | Parameter Type | Parameter Description |
| -------------- | -------------- | --------------------- |
| access_token | string | AccessToken with application identity authentication |
| refresh_token | string | Used to call refresh app token interface |
| expires_in | int | Valid time, the default validity period for the lesscode environment is 7 days |