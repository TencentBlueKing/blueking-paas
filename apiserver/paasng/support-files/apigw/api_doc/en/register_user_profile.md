### Function Description
Register the current user in the Developer Center. Users are registered automatically when they first visit the Developer Center in a browser. Users who have never visited it can register in advance through this API, which is required before they can be set as application administrators.

This API must be called with user credentials. Both the registered user and their tenant come from the user authenticated by the gateway, so it cannot register anyone else. Repeated calls do not modify an existing registration and return it as is.

If self-registration is disabled on the platform, the API returns 403 and the user must be added by a platform administrator.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Interface Parameters:
None.

### Request Example
```
curl -X POST -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***", "access_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/accounts/user_profile/
```

### Response Example
```
{
    "username": "admin",
    "tenant_id": "default",
    "role": 2
}
```

### Response Parameters Description

| Field | Type | Description |
|-------|------|-------------|
| username | string | Username |
| tenant_id | string | ID of the tenant the user belongs to |
| role | int | The user's role in the Developer Center, 2 for a regular user |
