### Description
Get deployment history

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID, e.g. "vision" |
| module   | string | Yes | Module name, e.g. "default" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{your_appcode}/modules/{your_module_name}/deployments/lists/
```

### Response Result Example
```json
{
    "count": 27,
    "next": "http://staging.bkpaas.example.com/backend/api/bkapps/applications/vision/modules/default/deployments/lists/?limit=12&offset=12",
    "previous": null,
    "results": [
        {
            "id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "status": "failed",
            "operator": {
                "id": "0227c0eb979e5289b5",
                "username": "admin",
                "provider_type": 2
            },
            "created": "2020-08-24 14:49:10",
            "deployment_id": "36ef5721-7313-48fa-a59a-1dc47c585828",
            "environment": "prod",
            "repo": {
                "source_type": "bk_gitlab",
                "type": "branch",
                "name": "master",
                "url": "http://git.example.com/v3-awesome-app.git",
                "revision": "141c46a87160afa4f33d280ddc368bf2c12fb5c7",
                "comment": ""
            }
        },
    ]
}
```

### Response Result Parameter Description

| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| count | integer | Yes | Total number of deployment history |
| next | string | No | Next page link |
| previous | string | No | Previous page link |
| results | array | Yes | Deployment history list |

results
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| id | string | Yes | Deployment history ID |
| status | string | Yes | Deployment status (successful, failed, pending) |
| operator | object | Yes | Operator information |
| created | string | Yes | Creation time |
| deployment_id | string | Yes | Deployment ID |
| environment | string | Yes | Deployment environment |
| repo | object | Yes | Repository information |

operator
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| id | string | Yes | Operator ID |
| username | string | Yes | Operator username |
| provider_type | integer | Yes | Provider type |

repo
| Field |   Type |  Required | Description |
| ------ | ------ | ------ | ------ |
| source_type | string | Yes | Repository source type |
| type | string | Yes | Branch type |
| name | string | Yes | Branch name |
| url | string | Yes | Repository URL |
| revision | string | Yes | Revision number |
| comment | string | Yes | Comment |