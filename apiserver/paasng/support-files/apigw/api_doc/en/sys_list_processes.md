### Description

Get the actual state of the processes and process instances of an AI Agent application environment with system API credentials. The caller must have the AIDEV system role and the target application must be an AI Agent application, otherwise a 403 is returned.

#### Tenant

The system API does not rely on user login state; the tenant is passed via the `X-Bk-Tenant-Id` header:

- Global apps (`app_tenant_mode` is `global`) are available to all tenants;
- Single-tenant apps are only available under the tenant matching their `app_tenant_id`, other tenants receive 403 `APP_TENANT_MISMATCH`;
- The header is ignored when multi-tenant mode is disabled.

### Request Parameters

#### 1. Path parameters

| Name | Type | Required | Description |
| -------- | -------- | --- | -------- |
| app_code | string | Yes | Application ID, must be an AI Agent application |
| module | string | Yes | Module name, e.g. "default" |
| env | string | Yes | Environment name, "stag" or "prod" |

#### 2. Query parameters

| Name | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| release_id | string | No | Release ID used to filter instances |

### Request Example

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -H 'X-Bk-Tenant-Id: default' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/processes/list/
```

### Response Example

Status: OK

```json
{
    "processes": {
        "items": [
            {
                "module_name": "default",
                "name": "ai-demo--web",
                "type": "web",
                "command": "",
                "replicas": 1,
                "success": 1,
                "failed": 0,
                "version": 3,
                "cluster_link": "http://ai-demo--web.bkapp-ai-demo-stag"
            }
        ],
        "extra_infos": [],
        "metadata": {
            "resource_version": "192437966"
        }
    },
    "instances": {
        "items": [
            {
                "module_name": "default",
                "name": "ai-demo--web-699599bf76-78jzf",
                "process_type": "web",
                "display_name": "78jzf",
                "image": "docker.example.com/bkpaas/docker/ai-demo/default:1.5.5",
                "start_time": "2024-08-16T02:07:55Z",
                "state": "Running",
                "state_message": null,
                "rich_status": "Running",
                "ready": true,
                "restart_count": 0,
                "version": "3"
            }
        ],
        "metadata": {
            "resource_version": "192437966"
        }
    },
    "process_packages": []
}
```

### Response Parameters

| Name | Type | Description |
| ------ | ------ | ------ |
| processes | object | Actual process state |
| instances | object | Actual process instance state |
| process_packages | array | Process configurations (target replicas, target status) |

Field details are identical to the user-facing `list_processes` API.
