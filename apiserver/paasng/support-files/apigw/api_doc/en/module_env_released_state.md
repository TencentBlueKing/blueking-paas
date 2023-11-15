### Description
Query application module environment deployment information

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | Yes      | Application code      |
| module_name    | string         | Yes      | Module name           |
| environment    | string         | Yes      | Environment name      |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

#### Get your access_token
Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### Response Result Example

#### Normal Return
```json
{
    "processes":[
        {
            "web":{
                "command":"gunicorn go.wsgi -b :$PORT --log-file -",
                "replicas":[
                    {
                        "status":"Running"
                    }
                ]
            }
        }
    ],
    "exposed_link":{
        "url":"http://apps.example.com/stag--appid/"
    },
    "deployment":{
        "id":"66e5d4fe-89d3-45bd-aa93-4d213815cc42",
        "status":"successful",
        "operator":{
            "username":"admin",
            "id":"0226c9f39893459abac3eb"
        },
        "created":"2017-06-14 11:22:06",
        "environment":"stag",
        "deployment_id":"66e5d4fe-89d3-45bd-aa93-4d213815cc42",
        "repo":{
            "url":"svn://svn.example.com:80/apps/ngdemo/trunk/__apps/go-appid/trunk",
            "comment":"",
            "type":"trunk",
            "name":"trunk",
            "revision":"183362"
        }
    },
    "feature_flag":{
        "release_to_bk_market": True/False,
        "release_to_wx_miniprogram": True/False,
        "release_to_wx_qiye": True/False
    },
    "module_mobile_config_enabled": True/False,
    "mobile_config": {
        "is_enabled": True/False,
        "access_domain": "https://balabala"
    }
}
```

#### Exception Return
```json
{
    "code": "APP_NOT_RELEASED",
    "detail": "The application has not been released in this environment"
}
```

### Response Result Parameter Description

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| processes | list | Yes | Process information |
| exposed_link | dict | Yes | Access address information |
| deployment | dict | Yes | Deployment information |
| feature_flag | dict | Yes | Release flag information |
| module_mobile_config_enabled | bool | Yes | Whether the mobile function is enabled |
| mobile_config | dict | Yes | Mobile configuration information |

processes
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| web | dict | Yes | Process information |

web
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| command | string | Yes | Process command |
| replicas | list | Yes | Process details |

replicas
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| status | string | Yes | Process status |

exposed_link
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| url | string | Yes | Access address |

deployment
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | string | Yes | Deployment ID |
| status | string | Yes | Deployment status |
| operator | dict | Yes | Deployment initiator information |
| created | string | Yes | Creation time |
| environment | string | Yes | Environment name |
| deployment_id | string | Yes | Deployment ID |
| repo | dict | Yes | Repository information |

repo
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| url | string | Yes | Repository URL |
| comment | string | Yes | Comment |
| type | string | Yes | Repository type |
| name | string | Yes | Repository name |
| revision | string | Yes | Repository revision |

