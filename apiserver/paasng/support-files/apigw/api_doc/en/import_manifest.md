### Description
Import manifest, update cloud-native app resources.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description            |
|----------------|----------------|----------|------------------------|
| app_code       | string         | Yes      | Application ID         |
| module         | string         | Yes      | Module name, e.g., "default" |
| env            | string         | Yes      | Environment name, options "stag" / "prod" |

#### 2. Body Parameters:

| Field    | Type   | Required | Description                              |
|----------|--------|----------|------------------------------------------|
| manifest | object | Yes      | JSON object of the cloud-native app model |


### Request Example

```json
{
  "manifest": {
    "apiVersion": "paas.bk.tencent.com/v1alpha1",
    "kind": "BkApp",
    "spec": {
      "processes": [
        {
          "cpu": "1000m",
          "args": [],
          "name": "web",
          "image": "nginx:latest",
          "memory": "256Mi",
          "command": [],
          "replicas": 1,
          "targetPort": 80
        }
      ],
      "configuration": {
        "env": []
      }
    }
  }
}
```

#### Obtain Your Access Token

Before using the API, please obtain your access token. Refer to [Accessing PaaS V3 with access_token](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Example

```json
[{
  "apiVersion": "paas.bk.tencent.com/v1alpha1",
  "kind": "BkApp",
  "metadata": {
    // Resource metadata, content omitted
  },
  "spec": {
    // App model configuration, content omitted
  },
  "status": {
    // Current resource status, content omitted
  }
}]
```

### Response Parameters Description

| Field      | Type   | Description               |
|------------|--------|---------------------------|
| apiVersion | string | API version               |
| kind       | string | Resource type             |
| metadata   | object | Resource metadata         |
| spec       | object | App model configuration   |
| status     | object | Current resource status   |