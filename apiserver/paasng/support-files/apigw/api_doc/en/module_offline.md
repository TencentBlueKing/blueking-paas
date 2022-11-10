### Resource Description
App off-shelf interface

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|
|   env | string |yes| Environment name, optional values 'stag'/'prod'|


### Call example
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AccessToken}}/modules/{{Fill in the name of your module}}/envs/{
Fill in the App deployment environment:stag or prod
}/offlines/
```

### Return result
```json
{
    "offline_operation_id": "22d0e9c8-9cfc-45a5-b5a8-718137c515db"
}
```

### Return result description
|   Field   | Type |           Description  |
| ------------ | ---------- | ------------------------------ |
|     offline_operation_id | string  | Downgrade Operation ID |