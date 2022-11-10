### Resource Description
Gets the AccessToken that represents the specified app and user identity

### Input parameter Description
|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   api_gateway_env | string |yes| Environment, optional values "test"/"prod"/"lesscode"|
| X-USER-BK-TICKET | string |yes| User's bk_ticket|

### Call example

```bash
curl -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' -H 'X-USER-BK-TICKET: {{Your bk_ticket }}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AppCode}}/oauth/token/{{api_gateway_env}}/ -H "COOKIE: bk_uid={{Your RTX}}&bk_ticket={{Your bk_ticket}}"
```

### Return result
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

### Return result description
|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|  access_token  | string |AccessToken with app authentication|
|  refresh_token  | string |Used to call the refresh app Refresh interface|
|  expires_in |int| Valid for 7 days by default for the lesscode environment|