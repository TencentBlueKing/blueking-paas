### Resource Description
Query app module environment deployment information

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

### Request parameter Description

| Name                                | Description |
| ----------------------------------- | ----------- |
| code * <br/>string<br/>(path)       | code        |
| environment *<br/>string<br/>(path) | environment |
| module_name *<br/>string<br/>(path) | module_name |

### Return result
#### Normal return
```json
{
    // Process information is only provided when passing with_processes
    "processes":[
        {
            "web":{
                "command":"gunicorn go.wsgi -b :$PORT --log-file -",
                "replicas":[                                            // Process details
                    {
                        "status":"Running"
                    }
                ]
            }
        }
    ],
    "exposed_link":{
        "url":"http://apps.example.com/stag--appid/"           // Access Address
    },
    "deployment":{
        "id":"66e5d4fe-89d3-45bd-aa93-4d213815cc42",
        "status":"successful",
        "operator":{
            "username":"admin",                                    // Deployment Initiators
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
        "release_to_bk_market": True/False,         # Whether to publish to BlueKing App Market
        "release_to_wx_miniprogram": True/False,    # Whether to publish to WeChat applet
        "release_to_wx_qiye": True/False            # Whether to publish to WeChat Enterprise
    },
    "module_mobile_config_enabled": True/False,     # Whether the mobile function is enabled or not (corresponding to the general switch of region)
    "mobile_config": {
        "is_enabled": True/False,                   # Whether to open the enterprise side of WeChat
        "access_domain": "https://balabala"         # Access Portal
    }
}
```

#### Abnormal return
```json
{
    "code": "APP_NOT_RELEASED",
    "detail": "The application has not been published in this environment"
}
```