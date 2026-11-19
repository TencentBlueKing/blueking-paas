### Function Description
Bind an addon service to an application module.

Recommended flow: call `list_module_services` to get the service `uuid`, call `list_service_possible_plans` for the plans, then call this API:

- `has_multiple_plans` is false: omit `plan_id` / `env_plan_id_map`; the platform uses the only plan.
- `static_plans` returned: pass one of them as `plan_id`.
- `env_specific_plans` returned: pass `env_plan_id_map` with a plan from each environment's own list; `plan_id` fails when an environment lacks that plan.

Omitting the plan while multiple plans exist fails with "unable to get available service plans". Redeploy after binding so credentials are injected as environment variables.

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. Body Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| code | string | Yes | Application ID |
| service_id | string | Yes | Addon service UUID from `list_module_services` `unbound[].uuid` |
| module_name | string | No | Module name; defaults to the application's default module |
| plan_id | string | No | Plan ID used by all environments |
| env_plan_id_map | object | No | Per-environment plan IDs, e.g. `{"stag": "<plan_id>", "prod": "<plan_id>"}` |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"code":"appid1","module_name":"default","service_id":"73f77c3a-dbc8-44cf-a6c5-3b1d656c4206"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/services/service-attachments/
```

### Response Example
```json
{
    "id": 1,
    "application": {
        "code": "appid1",
        "name": "demo"
    },
    "module_name": "default",
    "service": "73f77c3a-dbc8-44cf-a6c5-3b1d656c4206"
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Binding ID |
| application | object | Application info |
| module_name | string | Module name |
| service | string | Addon service UUID |

**Status Code Explanation:**
- **200**: Bound successfully
- **400**: Bind failed, e.g. no available plan or already bound
