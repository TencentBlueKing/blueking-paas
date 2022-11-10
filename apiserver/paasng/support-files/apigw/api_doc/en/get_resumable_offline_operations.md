### Resource Description
Query recoverable off-shelf operations

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|
|   env | string |yes| Environment name, optional values "stag"/"prod"|

### Call example

#### svn
```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AccessToken}}/modules/{{Fill in your module name}}/envs/{Fill in the App deployment environment:stag or prod}/offlines/resumable/
```

### Return result
```json
{
  "result": {
    "id": "--",
    "status": "successful",
    "operator": {
      "id": "--",
      "username": "--",
      "provider_type": 2
    },
    "created": datetime,
    "log": "try to stop process:web ...success to stop process: web\nall process stopped.\n",
    "err_detail": null,
    "offline_operation_id": "01e3617a-96b6-4bf3-98fb-1e27fc68c7ee",
    "environment": "stag",
    "repo": {
      "source_type": "--",
      "type": "--",
      "name": "--",
      "url": "--",
      "revision": "--",
      "comment": "--"
    }
  }
}
```

### Return result description

| id         | string($uuid)<br/>title: UUID<br/>readOnly: true             |
| ---------- | ------------------------------------------------------------ |
| status     | string<br/>title: Downline Status Enum:<br/>[ successful, failed, pending ] |
| operator   | string<br/>title: Operator<br/>readOnly: true                |
| created    | string($date-time)<br/>title: Created<br/>readOnly: true     |
| log        | string<br/>title: Offline Log<br/>x-nullable: true           |
| err_detail | string<br/>title: Reasons for downline anomalies<br/>x-nullable: true |



