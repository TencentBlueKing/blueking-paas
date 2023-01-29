### Resource Description

Query cnative app deploy status

### Get Your Access Token

Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Path Parameters

| Name     | Typr   | Required | Description                  |
|----------|--------|----------|------------------------------|
| app_code | string | ✓        | App ID                       |
| module   | string | ✓        | Module Name, such as default |
| env      | string | ✓        | Env Name (stag / prod)       |

### Call Example

```bash
curl -X GET http://bkapi.example.com/api/bkpaas3/prod/cnative/specs/applications/{app_code}/modules/{module}/envs/{env}/mres/status/ \
-H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' \
-H 'Content-Type: application/json'
```

### Return Result

```json
{
    "deployment": {
        "deploy_id": 2023,
        "status": "ready",
        "reason": "AppAvailable",
        "message": "",
        "last_transition_time": "2023-01-01T10:00:00+08:00",
        "operator": "admin",
        "created": "2023-01-01T10:00:00+08:00"
    },
    "ingress": {
        "url": "http://stag-dot-testcode.saas.bkexample.com/"
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
        "status": "True",
        "reason": "Provisioned",
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

### Return Result Description

| Name              | Type         | Description    |
|-------------------|--------------|----------------|
| deployment        | object       | deploy info    |
| deployment.status | string       | deploy status  |
| ingress           | object       | ingress info   |
| conditions        | list[object] | k8s conditions |
| events            | list[object] | k8s events     |
