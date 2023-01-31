### 资源描述

云原生应用部署接口

### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### 路径参数说明

| 参数名称      | 参数类型   | 必须  | 参数说明                      |
|-----------|--------|-----|---------------------------|
| app_code  | string | 是   | 应用 ID                     |
| module    | string | 是   | 模块名称，如 default            |
| env       | string | 是   | 环境名称，可选值 stag / prod   |

### 输入参数说明

| 参数名称         | 参数类型   |  必须  | 参数说明                                               |
|--------------|--------| ------ |----------------------------------------------------|
| manifest     | object |   是   | 云原生应用 manifest（Json 格式，可在开发者中心 - 应用编排 - YAML 页面获取） |

### 调用示例

#### curl

```bash
curl -X POST http://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/{app_code}/modules/{module}/envs/{env}/mres/deployments/ \
--header 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' \
--header 'Content-Type: application/json' \
--data-raw '{
    "manifest": {
        "apiVersion": "paas.bk.tencent.com/v1alpha1",
        "kind": "BkApp",
        "metadata": {
            "annotations": {
                "bkapp.paas.bk.tencent.com/addons": "[\"mysql\"]"
            },
            "name": "testcode"
        },
        "spec": {
            "configuration": {
                "env": []
            },
            "envOverlay": {
                "envVariables": [
                    {
                        "envName": "stag",
                        "name": "FOO",
                        "value": "stag_value"
                    }
                ]
            },
            "processes": [
                {
                    "args": [],
                    "command": [
                        "bash",
                        "/app/start_web.sh"
                    ],
                    "cpu": "4000m",
                    "image": "hub.bktencent.com/blueking/django-helloworld:latest",
                    "imagePullPolicy": "IfNotPresent",
                    "memory": "1024Mi",
                    "name": "web",
                    "replicas": 1
                }
            ]
        }
    }
}'
```

### 返回结果

```json
{
    "apiVersion": "paas.bk.tencent.com/v1alpha1",
    "kind": "BkApp",
    "metadata": {
        ...
    },
    "spec": {
        ...
    },
    "status": {
        ...
    }
}
```
