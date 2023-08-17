### Feature Description
Get all process and instance information for the application environment

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | -------------------- |
| app_code       | string         | Yes      | App Code            |
| environment    | string         | Yes      | Runtime Environment |
| module_name    | string         | Yes      | Module Name         |

#### 2. Interface Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/envs/prod/processes/list/
```

### Response Result Example
Status: OK

### Response Result Parameter Description

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| instances | ListProcessesOKBodyInstances | Yes | All instance statuses |
| process_packages | []ListProcessesOKBodyProcessPackagesItems0 | Yes | Process configuration status on the platform |
| processes | ListProcessesOKBodyProcesses | Yes | Current process status |

**ListProcessesOKBodyInstancesItemsItems0**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| display_name | string | Yes | Short name for display |
| name | string | Yes | Instance name |
| process_type | string | Yes | Process type name |
| ready | boolean | Yes | Whether the instance is ready |
| start_time | string | Yes | Instance start time |
| state | string | Yes | Instance status, possible values: "Running" / "Starting" etc. |
| version | integer | Yes | Instance release version number, the client can use this value to compare with Process to determine if the instance is the latest version |

**ListProcessesOKBodyProcessPackagesItems0**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| max_replicas | integer | Yes | Maximum number of instances allowed by the backend |
| name | string | Yes | Process type, such as "web" |
| resource_limit | string | Yes | CPU and memory limit information |
| target_replicas | integer | Yes | User-set target replica count |
| target_status | integer | Yes | User-set target status |

**ListProcessesOKBodyProcessesItemsItems0**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| failed | integer | Yes | Error (failed) instance count |
| name | string | Yes | Process name |
| replicas | integer | Yes | Process set (expected) instance count |
| success | integer | Yes | Normal instance count |
| type | string | Yes | Process type |
| version | integer | Yes | Process release version number |