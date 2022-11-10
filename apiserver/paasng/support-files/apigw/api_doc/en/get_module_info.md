### Resource Description
View app module information

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path interface description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   yes   | App ID    |
|   module |   string     |   yes   | Module name, such as "default"|



### Call example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AccessToken}}/modules/{{Fill in your module name}}/
```

### Return result
```json
{
  "id": "--",
  "repo": {
    "source_type": "--",
    "type": "--",
    "trunk_url": "--",
    "repo_url": "--",
    "repo_fullname": "--",
    "use_external_diff_page": bool,
    "linked_to_internal_svn": bool,
    "display_name": "--"
  },
  "web_config": {
    "can_publish_to_market": bool,
    "confirm_required_when_publish": bool,
    "market_published": bool,
    "engine_enabled": bool
  },
  "template_display_name": "--",
  "source_origin": int,
  "region": "ieod",
  "created": datetime,
  "updated": datetime,
  "owner": "--",
  "name": "default",
  "is_default": bool,
  "language": "--",
  "source_init_template": "--",
  "exposed_url_type": 2,
  "last_deployed_date": datetime,
  "creator": "--",
  "application": "--"
}
```

### Return result description

| id                    | string($uuid)<br/>title: UUID<br/>readOnly: true             |
| --------------------- | ------------------------------------------------------------ |
| repo*                 | dict, see the table below for field details                  |
| web_config            | dict, see the table below for field details                  |
| template_display_name | string<br/>title: Template display name<br/>readOnly: true   |
| source_origin*        | integer<br/>title: Source origin                             |
| region*               | string<br/>title: Region<br/>maxLength: 32<br/>minLength: 1<br/>Deployment area, e.g. internal version is ieod |
| created               | string($date-time)<br/>title: Created<br/>readOnly: true     |
| updated               | string($date-time)<br/>title: Updated<br/>readOnly: true     |
| owner                 | string<br/>title: Owner<br/>maxLength: 64<br/>x-nullable: true |
| name*                 | string<br/>title: Module Name<br/>maxLength: 20<br/>minLength: 1 |
| is_default            | boolean<br/>title: Whether it is the default module          |
| language*             | string<br/>title: Programming Languages<br/>maxLength: 32<br/>minLength: 1 |
| source_init_template* | string<br/>title: Initialize template type<br/>maxLength: 32<br/>minLength: 1 |
| exposed_url_type      | integer<br/>title: Access URL version<br/>maximum: 2147483647<br/>minimum: -2147483648<br/>x-nullable: true |
| last_deployed_date    | string($date-time)<br/>title: Latest deployment time<br/>x-nullable: true |
| creator               | string<br/>title: Creator<br/>maxLength: 64<br/>x-nullable: true |
| application*          | string($uuid)<br/>title: Application                         |

#### repo Field Detail

| description:           | Source Code Library Information                              |
| ---------------------- | ------------------------------------------------------------ |
| source_type*           | string<br/>title: Source type<br/>minLength: 1               |
| type*                  | string<br/>title: Type<br/>minLength: 1                      |
| trunk_url              | string<br/>title: Trunk url<br/>readOnly: true<br/>x-nullable: true<br/>[deprecated] Should only work for svn repo |
| repo_url               | string<br/>title: Repo url<br/>readOnly: true<br/>x-nullable: true<br/>Repo url display in frontend. |
| repo_fullname*         | string<br/>title: Repo fullname<br/>minLength: 1<br/>Repo fullname |
| use_external_diff_page | boolean<br/>title: Use external diff page<br/>default: false |
| linked_to_internal_svn | boolean<br/>title: Linked to internal svn<br/>default: true  |
| display_name*          | string<br/>title: Display name<br/>minLength: 1              |

#### web_config Field Detail

| can_publish_to_market         | boolean<br/>title: Can the module be released to the market<br/>default: false |
| ----------------------------- | ------------------------------------------------------------ |
| confirm_required_when_publish | boolean<br/>title: When posting to the market, is secondary confirmation required<br/>default: false |
| market_published              | boolean<br/>title: Whether it has been released to the market<br/>default: false |
| engine_enabled                | boolean<br/>title: Whether the module enables the app engine<br/>default: false |