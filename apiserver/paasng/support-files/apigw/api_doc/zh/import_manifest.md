### 功能描述
导入 manifest,更新云原生应用资源。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |

#### 2、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| manifest | object | 是 | 云原生应用的应用模型 Json 对象。位置请求Body |


### 请求示例
```bash
curl -X PUT -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***", "bk_token": "***"}' -d '{ "manifest": { "apiVersion": "example.com/v1alpha2", "kind": "BkApp", "metadata": { "annotations": { "bkapp.example.com/code": "test", "bkapp.example.com/image-credentials": "test--dockerconfigjson", "bkapp.example.com/module-name": "default", "bkapp.example.com/name": "test", "bkapp.example.com/region": "default" }, "name": "test" }, "spec": { "addons": [ ], "build": { "imagePullPolicy": "IfNotPresent" }, "configuration": { "env": [ ] }, "envOverlay": { "envVariables": [ ] }, "hooks": { }, "mounts": [ ], "processes": [ { "args": [ ], "command": [ ], "name": "web", "replicas": 4, "resQuotaPlan": "default", "targetPort": 5000 } ] } } }' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/test/modules/default/bkapp_model/manifests/current/
```
#### 请求体示例
```json
{
    "manifest": {
        "apiVersion": "example.com/v1alpha2",
        "kind": "BkApp",
        "metadata": {
            "annotations": {
                "bkapp.example.com/code": "test",
                "bkapp.example.com/image-credentials": "test--dockerconfigjson",
                "bkapp.example.com/module-name": "default",
                "bkapp.example.com/name": "test",
                "bkapp.example.com/region": "default"
            },
            "name": "test"
        },
        "spec": {
            "addons": [
            ],
            "build": {
                "imagePullPolicy": "IfNotPresent"
            },
            "configuration": {
                "env": [
                ]
            },
            "envOverlay": {
                "envVariables": [
                ]
            },
            "hooks": {
            },
            "mounts": [
            ],
            "processes": [
                {
                    "args": [
                    ],
                    "command": [
                    ],
                    "name": "web",
                    "replicas": 2,
                    "resQuotaPlan": "default",
                    "targetPort": 5000
                }
            ]
        }
    }
}
```
manifest.metafata.name应该等于应用的名称


### 返回结果示例
#### 正常返回
```json
[
    {
        "apiVersion": "example.com/v1alpha2",
        "kind": "BkApp",
        "metadata": {
            "name": "test",
            "annotations": {
                "bkapp.example.com/region": "default",
                "bkapp.example.com/name": "test",
                "bkapp.example.com/code": "test",
                "bkapp.example.com/module-name": "default",
                "bkapp.example.com/image-credentials": "test--dockerconfigjson"
            }
        },
        "spec": {
            "build": {
                "imagePullPolicy": "IfNotPresent"
            },
            "processes": [
                {
                    "name": "web",
                    "replicas": 4,
                    "command": [],
                    "args": [],
                    "targetPort": 5000,
                    "resQuotaPlan": "default"
                }
            ],
            "hooks": {},
            "addons": [],
            "mounts": [],
            "configuration": {
                "env": []
            },
            "envOverlay": {
                "envVariables": []
            }
        }
    }
]
```
#### 异常返回
捕获到异常时返回示例：
```json
{
    "code": "VALIDATION_ERROR",
    "detail": "apiVersion ... is not valid, ...",
    "fields_detail": [
        "apiVersion ... is not valid, ..."
    ]
}
```
当manifest配置错且异常未捕获到， 会返回http状态500


### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| apiVersion | string | API 版本 |
| kind | string | 资源类型 |
| metadata | object | 资源元信息 |
| spec | object | 应用模型配置 |