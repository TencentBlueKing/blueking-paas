### 功能描述
查询应用模块环境部署信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| code     | string   | 是   | 应用代码 |
| module_name | string | 是 | 模块名称 |
| environment | string | 是 | 环境名称 |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### 返回结果示例

#### 正常返回
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

#### 异常返回
```json
{
    "code": "APP_NOT_RELEASED",
    "detail": "应用尚未在该环境发布过"
}
```

### 返回结果参数说明

| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| processes | list | 是 | 进程信息 |
| exposed_link | dict | 是 | 访问地址信息 |
| deployment | dict | 是 | 部署信息 |
| feature_flag | dict | 是 | 发布标志信息 |
| module_mobile_config_enabled | bool | 是 | 移动端功能是否开启 |
| mobile_config | dict | 是 | 移动端配置信息 |

processes
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| web | dict | 是 | 进程信息 |

web
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| command | string | 是 | 进程命令 |
| replicas | list | 是 | 进程详情 |

replicas
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| status | string | 是 | 进程状态 |

exposed_link
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| url | string | 是 | 访问地址 |

deployment
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| id | string | 是 | 部署ID |
| status | string | 是 | 部署状态 |
| operator | dict | 是 | 部署发起人信息 |
| created | string | 是 | 创建时间 |
| environment | string | 是 | 环境 |
| deployment_id | string | 是 | Deployment ID |
| repo | dict | 是 | 代码仓库信息 |

repo
| 字段 | 类型 | 是否必填 | 描述 |
| ---- | ---- | -------- | ---- |
| url | string | 是| 代码仓库地址 |
| comment | string | 是 | Comment |
| type | string | 是 | 代码仓库类型 |
| name | string | 是| 代码仓库名称|
| revision | string | 是 | 代码仓库版本 |
