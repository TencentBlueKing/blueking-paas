### Description

Get the current deployment status of the cloud-native application in the specified environment.

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name, such as "default" |
| env            | string         | Yes      | Environment name, optional values "stag" / "prod" |

#### 2. API Parameters:
None


### Request Example

```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "access_token": "{{Fill in your AccessToken}}"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/{app_code}/modules/{module}/envs/{env}/mres/status/
```

#### Get your access_token

Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Result Example

```json
{
  "deployment": {
    "deploy_id": 1,
    "status": "ready",
    "reason": "AppAvailable",
    "message": "",
    "last_transition_time": "2023-01-05T15:01:30+08:00",
    "operator": "user",
    "created": "2023-01-05T15:01:15.524240+08:00"
  },
  "ingress": {
    "url": "http://.../"
  },
  "conditions": [
    {
      "type": "AppAvailable",
      "status": "True",
      "reason": "AppAvailable",
      "message": ""
    },
    {
      "type": "AppProgressing",
      "status": "True",
      "reason": "NewRevision",
      "message": ""
    },
    {
      "type": "AddOnsProvisioned",
      "status": "Unknown",
      "reason": "Initial",
      "message": ""
    },
    {
      "type": "HooksFinished",
      "status": "True",
      "reason": "Finished",
      "message": ""
    }
  ],
  "events": []
}
```

### Response Result Parameter Description

| Parameter Name | Parameter Type | Parameter Description              |
| -------------- | -------------- | ----------------------------------- |
| deployment     | object         | Latest deployment status overview  |
| ingress        | object         | Externally exposed accessible URL  |
| conditions     | array[object]  | Current detailed status of the resource |

`deployment` field detailed description:

| Parameter Name | Parameter Type | Parameter Description                                             |
| -------------- | -------------- | ------------------------------------------------------------------ |
| status         | string         | Current deployment status, optional values: pending / progressing / ready / error / unknown, where ready means the deployment is completed normally |