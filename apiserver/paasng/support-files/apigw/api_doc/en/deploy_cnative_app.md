### Description
Deploy cloud-native applications.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name, e.g., "default" |
| env            | string         | Yes      | Environment name, optional values: "stag" / "prod" |

#### 2. API Parameters:

| Field     | Type   | Required | Description                              |
| --------- | ------ | -------- | ---------------------------------------- |
| manifest  | object | Yes      | Json object of the cloud-native application model |


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

#### Get your access_token

Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Result Example

```json
{
  "apiVersion": "paas.bk.tencent.com/v1alpha1",
  "kind": "BkApp",
  "metadata": {
    // Resource metadata, content omitted
  },
  "spec": {
    // Application model configuration, content omitted
  },
  "status": {
    // Current resource status, content omitted
  }
}
```

### Response Result Parameter Description

| Field       | Type   | Description            |
| ----------- | ------ | ---------------------- |
| apiVersion  | string | API version            |
| kind        | string | Resource type          |
| metadata    | object | Resource metadata      |
| spec        | object | Application model configuration |
| status      | object | Current resource status |