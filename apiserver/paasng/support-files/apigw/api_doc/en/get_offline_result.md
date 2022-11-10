### Resource Description
Query off-shelf task result

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|
|   offline_operation_id | string |yes| UUID of the off-shelf task|

### Call example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AccessToken}}/modules/{{Fill in your module name}}/envs/{Fill in the App deployment environment:stag or prod}/offlines/{{offline_operation_id}}/result/
```

### Return result
```json
{
    "status": "str",
    "error_detail": "str",
    "logs": "str"
}
```

### Return result description

| status       | string <br/>example: failed<br/>offline task status (successful, pending, or failed) |
| ------------ | ------------------------------------------------------------ |
| error_detail | string <br/>example: failed<br/>error message                |
| logs         | string <br/>example: Starting stop`web` process<br/>offline log |

