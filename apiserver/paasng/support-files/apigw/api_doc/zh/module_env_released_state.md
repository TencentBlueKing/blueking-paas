### 资源描述
查询应用模块环境部署信息

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 调用示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

### 请求参数说明
<table class="parameters"><thead><tr><th class="col_header parameters-col_name">Name</th><th class="col_header parameters-col_description">Description</th></tr></thead><tbody><tr data-param-name="code" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10603 -->code<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10606 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10609 -->(<!-- /react-text --><!-- react-text: 10610 -->path<!-- /react-text --><!-- react-text: 10611 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="code" value="" disabled=""></td></tr><tr data-param-name="environment" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10617 -->environment<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10620 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10623 -->(<!-- /react-text --><!-- react-text: 10624 -->path<!-- /react-text --><!-- react-text: 10625 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="environment" value="" disabled=""></td></tr><tr data-param-name="module_name" data-param-in="path"><td class="parameters-col_name"><div class="parameter__name required"><!-- react-text: 10631 -->module_name<!-- /react-text --><span style="color: red;">&nbsp;*</span></div><div class="parameter__type"><!-- react-text: 10634 -->string<!-- /react-text --></div><div class="parameter__deprecated"></div><div class="parameter__in"><!-- react-text: 10637 -->(<!-- /react-text --><!-- react-text: 10638 -->path<!-- /react-text --><!-- react-text: 10639 -->)<!-- /react-text --></div></td><td class="parameters-col_description"><input type="text" class="" title="" placeholder="module_name" value="" disabled=""></td></tr></tbody></table>

### 返回结果
#### 正常返回
```json
{
    // 进程信息仅当传递 with_processes 时提供
    "processes":[
        {
            "web":{
                "command":"gunicorn go.wsgi -b :$PORT --log-file -",
                "replicas":[                                            // 进程详情
                    {
                        "status":"Running"
                    }
                ]
            }
        }
    ],
    "exposed_link":{
        "url":"http://apps.example.com/stag--appid/"           // 访问地址
    },
    "deployment":{
        "id":"66e5d4fe-89d3-45bd-aa93-4d213815cc42",
        "status":"successful",
        "operator":{
            "username":"admin",                                    // 部署发起人
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
        "release_to_bk_market": True/False,         # 是否发布到蓝鲸应用市场
        "release_to_wx_miniprogram": True/False,    # 是否发布到微信小程序
        "release_to_wx_qiye": True/False            # 是否发布到微信企业端
    },
    "module_mobile_config_enabled": True/False,     # 移動端功能是否开启(对应region的总开关)
    "mobile_config": {
        "is_enabled": True/False,                   # 是否开启微信企业号端,
        "access_domain": "https://balabala"         # 访问入口
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