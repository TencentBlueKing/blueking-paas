### Description

Fetch an access token for an AI Agent application with application credentials, on behalf of the given user. The caller must have the AIDEV system role and the target application must be an AI Agent application, otherwise a 403 is returned.

The caller must provide the user's Developer Center login credential (`bk_ticket` / `bk_token`) in a request header, and the platform resolves the user identity from that credential.

### Request Parameters

#### 1. Path parameters

| Name | Type | Required | Description |
| -------- | -------- | --- | -------- |
| app_code | string | Yes | Application ID, must be an AI Agent application |
| env_name | string | Yes | Environment, optional values: "test" / "prod" |

#### 2. Request headers

Exactly one of the two headers must be provided; which one depends on the auth backend the platform uses.

| Header | Type | Required | Description |
| -------- | -------- | --- | -------- |
| X-USER-BK-TICKET | string | One of the two | The user's bk_ticket, required when the platform uses bk_ticket |
| X-USER-BK-TOKEN | string | One of the two | The user's bk_token, required when the platform uses bk_token |

The credential type must match the platform's auth backend; the header of the other type is ignored. A multi-tenant deployment can only use `bk_token`.

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-USER-BK-TICKET: {{your bk_ticket}}' --insecure 'https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/oauth/token/prod/'
```

### Response Example

```json
{
    "access_token": "--",
    "refresh_token": "--",
    "expires_in": 604784
}
```

### Response Result Parameter Description

| Name | Type | Description |
| -------- | -------- | -------- |
| access_token | string | AccessToken with application identity authentication |
| refresh_token | string | Used to call the refresh app token API |
| expires_in | int | Valid time, decided by the upstream token service |
