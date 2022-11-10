### Resource Description
View application information

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path parameter

|   Field   |    Type  |  Required  |     Description     |
|----------|----------|-----|--------|
| app_code | string   | yes   |  App ID, e.g. "Monitor"  |

### Call example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{YourAppCode}}/
```

### 返回结果

```json
// The content is too long and is temporarily omitted. Please view the field details directly through the form below
```

### 返回结果说明

`.application` 成员对象各字段说明:

| Name          | Type          | Description                               |
|--------------------|-------------------|----------------------------------------|
| id                 | string(uuid)      | UUID                                   |
| name               | string            |                                        |
| region_name        | string            |                            |
| logo_url           | string            |                       |
| config_info        |                   |                      |
| modules            |                   |                      |
| region             | string            |                                |
| created            | string(date-time) |                                        |
| updated            | string(date-time) |                                        |
| owner              | string            |                                        |
| code               | string            |                                |
| name_en            | string            |  |
| type               | string            |                                |
| is_smart_app       | boolean           |                    |
| language           | string            |                                |
| creator            | string            |                                        |
| is_active          | boolean           |                                |
| is_deleted         | boolean           |                                |
| last_deployed_date | string(date-time) |                            |

`.web_config` member object field description:

| Name          | Type          | Description                               |
|-------------------------------|----------|------------------------------|
| engine_enabled                | bool     |                  |
| can_create_extra_modules      | bool     |              |
| require_templated_source      | bool     |  |
| confirm_required_when_publish | bool     |      |
| market_published              | bool     |            |
