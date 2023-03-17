### Resource Description

Deploy cnative app api

### Get Your Access Token

Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path Parameters

| Name     | Type   | Required | Description                  |
|----------|--------|----------|------------------------------|
| app_code | string | ✓        | App ID                       |
| module   | string | ✓        | Module Name, such as default |
| env      | string | ✓        | Env Name (stag / prod)       |

### Input Parameters Description

| Name     | Type   | Required | Description                        |
|----------|--------|----------|------------------------------------|
| manifest | object | ✓        | cnative app manifest (json format) |

### Call Example

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
                    "cpu": "500m",
                    "image": "hub.bktencent.com/blueking/django-helloworld:latest",
                    "imagePullPolicy": "IfNotPresent",
                    "memory": "256Mi",
                    "name": "web",
                    "replicas": 1
                }
            ]
        }
    }
}'
```

### Return Result

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
