### Description
Import manifest, update cloud-native app resources.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description            |
|----------------|----------------|----------|------------------------|
| app_code       | string         | Yes      | Application ID         |
| module         | string         | Yes      | Module name, e.g., "default" |

#### 2. Body Parameters:

| Field    | Type   | Required | Description                              |
|----------|--------|----------|------------------------------------------|
| manifest | object | Yes      | JSON object of the cloud-native app model |


### Request Example

```bash
curl -X PUT -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***", "bk_token": "***"}' -d '{ "manifest": { "apiVersion": "example.com/v1alpha2", "kind": "BkApp", "metadata": { "annotations": { "bkapp.example.com/code": "test", "bkapp.example.com/image-credentials": "test--dockerconfigjson", "bkapp.example.com/module-name": "default", "bkapp.example.com/name": "test", "bkapp.example.com/region": "default" }, "name": "test" }, "spec": { "addons": [ ], "build": { "imagePullPolicy": "IfNotPresent" }, "configuration": { "env": [ ] }, "envOverlay": { "envVariables": [ ] }, "hooks": { }, "mounts": [ ], "processes": [ { "args": [ ], "command": [ ], "name": "web", "replicas": 4, "resQuotaPlan": "default", "targetPort": 5000 } ] } } }' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/test/modules/default/bkapp_model/manifests/current/
```
#### Request Body Example
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
manifest.metafata.name should be equal to the name of the application.

### Response Example
#### Success Response
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

#### Exception Response
Example of returning when an exception is caught:
```json
{
    "code": "VALIDATION_ERROR",
    "detail": "apiVersion ... is not valid, ...",
    "fields_detail": [
        "apiVersion ... is not valid, ..."
    ]
}
```
When the manifest is misconfigured and the exception is not caught, the http status 500 is returned.


### Response Parameters Description

| Field      | Type   | Description               |
|------------|--------|---------------------------|
| apiVersion | string | API version               |
| kind       | string | Resource type             |
| metadata   | object | Resource metadata         |
| spec       | object | App model configuration   |