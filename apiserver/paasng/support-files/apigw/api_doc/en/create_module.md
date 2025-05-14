### Description
Create a module

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID |

#### 2. API Parameters:

| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| name | string | Yes | Module name |
| source_config | dict | Yes | Source configuration |
| bkapp_spec | dict | Yes | Application specification |

source_config
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| source_init_template | string | Yes | Source initialization template |
| source_origin | int | Yes | Source origin |

bkapp_spec
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| build_config | dict | Yes | Build configuration |

build_config
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| build_method | string | Yes | Build method, e.g. "buildpack" |

### Request Example
```
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{ "name": "dd1", "source_config": { "source_init_template": "dj2_with_auth", "source_origin": 2 }, "bkapp_spec": { "build_config": { "build_method": "buildpack" } } }' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

### Response Example
```
{
    "module": {
        "id": "d3a06af5-3d70-4e56-8380-44ec3d41dded",
        "repo": {
            "source_type": "",
            "type": "",
            "trunk_url": null,
            "repo_url": null,
            "source_dir": "",
            "repo_fullname": null,
            "diff_feature": {},
            "linked_to_internal_svn": false,
            "display_name": ""
        },
        "repo_auth_info": {},
        "web_config": {
            "templated_source_enabled": false,
            "runtime_type": "buildpack",
            "build_method": "buildpack",
            "artifact_type": "slug"
        },
        "template_display_name": "Blueking Application Development Framework (Django3.x)",
        "source_origin": 2,
        "region": "ieod",
        "created": "2024-05-09 19:32:50",
        "updated": "2024-05-09 19:32:50",
        "owner": "023ec1eb8c894a90",
        "name": "dd1",
        "is_default": false,
        "language": "Python",
        "source_init_template": "dj2_with_auth",
        "exposed_url_type": 2,
        "user_preferred_root_domain": null,
        "last_deployed_date": null,
        "creator": "023ec1eb8c894a90",
        "application": "a9f88dd9-0779-496a-b2c0-9200f06dbec7"
    },
    "source_init_result": {}
}
```

### Response Parameters Description

| Field |   Type | Description |
| ------ | ------ | ------ |
| module | dict | Module information |
| source_init_result | dict | Source initialization result |

module
| Field |   Type | Description |
| ------ | ------ | ------ |
| id | string | Module ID |
| repo | dict | Repository information |
| repo_auth_info | dict | Repository authentication information |
| web_config | dict | Web configuration |
| template_display_name | string | Template display name |
| source_origin | int | Source origin |
| region | string | Region |
| created | string | Creation time |
| updated | string | Update time |
| owner | string | Owner |
| name | string | Module name |
| is_default | boolean | Whether it is the default module |
| language | string | Module language |
| source_init_template | string | Source initialization template |
| exposed_url_type | int | Exposed URL type |
| user_preferred_root_domain | string | User preferred root domain |
| last_deployed_date | string | Last deployment date |
| creator | string | Creator |
| application | string | Application ID |