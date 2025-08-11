### Description
View application information


### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
|----------------|----------------|----------|-----------------------|
| app_code       | string         | Yes      | Application ID        |

#### 2. API Parameters:
None.

### Request Example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AppCode}}/
```

### Response Result Example

```json
// Content is too long, temporarily omitted. Please refer to the table below for field details.
```

### Response Result Parameter Description

`.application` member object field description:

| Parameter Name           | Parameter Type    | Parameter Description                  |
|--------------------------|-------------------|----------------------------------------|
| id                       | string(uuid)      | Application UUID                                   |
| name                     | string            | Application name                                      |
| region_name              | string            | Application version name               |
| logo_url                 | string            | Application Logo URL                   |
| config_info              | dict              | Additional status information of the application |
| modules                  | dict              | List of application module information |
| region                   | string            | Deployment region                      |
| created                  | string(date-time) | Created time                                       |
| updated                  | string(date-time) | Updated time                                       |
| owner                    | string            |  Application owner                                      |
| code                     | string            | Application code                       |
| name_en                  | string            | Application name (English); currently only used for S-Mart applications |
| type                     | string            | Application type                       |
| is_smart_app             | boolean           | Is it an S-Mart application            |
| language                 | string            | Programming language                   |
| creator                  | string            | Application creator                                       |
| is_active                | boolean           | Is it active                           |
| is_deleted               | boolean           | Is it deleted                          |
| last_deployed_date       | string(date-time) | Last deployment time                   |

`.web_config` member object field description:

| Parameter Name                      | Parameter Type | Parameter Description                  |
|-------------------------------------|----------------|----------------------------------------|
| engine_enabled                      | bool           | Is the application engine enabled      |
| can_create_extra_modules            | bool           | Can additional modules be created      |
| confirm_required_when_publish       | bool           | Is a second confirmation required when publishing to the market |
| market_published                    | bool           | Has it been published to the application market |