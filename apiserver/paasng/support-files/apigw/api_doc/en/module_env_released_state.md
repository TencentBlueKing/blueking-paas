### Description
Query application module environment deployment information

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | Yes      | Application code      |
| module_name    | string         | Yes      | Module name           |
| environment    | string         | Yes      | Environment name      |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_state/
```

### Response Result Example

#### Normal Return
```json
{
    "is_offlined": false,
    "deployment": {
        "id": "114392d8-9e77-4011-83a9-41f1737e2466",
        "status": "successful",
        "operator": {
            "id": "0335cce79c92",
            "username": "admin",
            "provider_type": 3,
            "avatar": ""
        },
        "created": "2024-08-16 10:07:33",
        "start_time": "2024-08-16 10:07:33",
        "complete_time": "2024-08-16 10:08:07",
        "finished_status": "release",
        "build_int_requested_at": null,
        "release_int_requested_at": null,
        "has_requested_int": false,
        "bkapp_revision_id": 247,
        "deployment_id": "114392d8-9e77-4011-83a9-41f1737e2466",
        "environment": "prod",
        "repo": {
            "source_type": null,
            "type": "tag",
            "name": "1.5.5",
            "url": "docker.example.com/bkpaas/docker/example/default:1.5.5",
            "revision": "1.5.5",
            "comment": ""
        }
    },
    "offline": null,
    "exposed_link": {
        "url": "http://apps.example.com/"
    },
    "default_access_entrance": {
        "url": "http://apps.example.com/"
    }
}
```

#### Exception Return
```json
{
    "code": "APP_NOT_RELEASED",
    "detail": "The application has not been released in this environment"
}
```

### Response Result Parameter Description

| Field | Type |  Description |
| ----- | ---- |  ----------- |
| is_offlined | boolean | Whether the module is offline in this environment |
| deployment | object | Deployment record |
| offline | object | Offline record |
| exposed_link | object | Access address |
| default_access_entrance | object | Default access address |
