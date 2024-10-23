### Description
Get all process and instance information for the application environment

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | -------------------- |
| app_code       | string         | Yes      | App Code            |
| environment    | string         | Yes      | Runtime Environment |
| module_name    | string         | Yes      | Module Name         |

#### 2. API Parameters:
| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | -------------------- |
| only_latest_version | boolean | No | Whether to show only the last version of the process |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/envs/prod/processes/list/
```

### Response Result Example

```json
{
    "processes": {
        "items": [
            {
                "module_name": "default",
                "name": "example--web",
                "type": "web",
                "command": "",
                "replicas": 5,
                "success": 5,
                "failed": 0,
                "version": 175,
                "cluster_link": "http://example--web.bkapp-example-prod"
            }
        ],
        "extra_infos": [
            {
                "type": "web",
                "command": "",
                "cluster_link": "http://example--web.bkapp-example-prod"
            }
        ],
        "metadata": {
            "resource_version": "192437966"
        }
    },
    "instances": {
        "items": [
            {
                "module_name": "default",
                "name": "example--web-699599bf76-78jzf",
                "process_type": "web",
                "display_name": "78jzf",
                "image": "docker.example.com/bkpaas/docker/example/default:1.5.5",
                "start_time": "2024-08-16T02:07:55Z",
                "state": "Running",
                "state_message": null,
                "rich_status": "Running",
                "ready": true,
                "restart_count": 0,
                "version": "175"
            }
        ],
        "metadata": {
            "resource_version": "192437966"
        }
    },
    "cnative_proc_specs": [
        {
            "name": "web",
            "target_replicas": 5,
            "target_status": "start",
            "max_replicas": 10,
            "resource_limit": {
                "cpu": "4000m",
                "memory": "2048Mi"
            },
            "resource_requests": {
                "cpu": "200m",
                "memory": "1024Mi"
            },
            "plan_name": "4C2G",
            "resource_limit_quota": {
                "cpu": 4000,
                "memory": 2048
            },
            "autoscaling": false,
            "scaling_config": null,
            "cpu_limit": "4000m",
            "memory_limit": "2048Mi"
        }
    ]
}
```

### Response Result Parameter Description
| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| processes             | object   | Processes information   |
| instances             | object   | Instances information   |
| cnative_proc_specs    | object   | Cloud native process specifications   |

#### .processes filed descriptionn

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| items                 | array    | A list of process items.                                  |
| extra_infos           | array    | Additional information about the processes.               |
| metadata              | object   | Metadata related to the processes.                        |

.process.items

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| module_name           | string   | The name of the module associated with the process.       |
| name                  | string   | The name of the process.                                  |
| type                  | string   | The type of process (e.g., web).                         |
| command               | string   | The command executed by the process.                      |
| replicas              | integer  | The number of process replicas running.                   |
| success               | integer  | The number of successful replicas.                        |
| failed                | integer  | The number of failed replicas.                            |
| version               | integer  | The version of the process.                               |
| cluster_link          | string   | The URL link to the cluster where the process is running. |

.process.extra_infos

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| type                  | string   | The type of process (e.g., web).                         |
| command               | string   | The command executed by the process.                      |
| cluster_link          | string   | The URL link to the cluster where the process is running. |

.process.metadata

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| resource_version      | string   | The resource version of the processes.                    |


#### .instances filed descriptionn

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| items                 | array    | A list of instance items.                                  |
| metadata              | object   | Metadata related to the instances.                        |

.instances.items

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| module_name           | string   | The name of the module associated with the instance.       |
| name                  | string   | The name of the instance.                                  |
| process_type          | string   | The type of process for the instance (e.g., web).         |
| display_name          | string   | A display name for the instance.                           |
| image                 | string   | The Docker image used by the instance.                     |
| start_time            | string   | The start time of the instance in ISO 8601 format.         |
| state                 | string   | The current state of the instance (e.g., Running).       |
| state_message         | string   | An optional message detailing the state of the instance.   |
| rich_status           | string   | A human-readable representation of the instance's status.  |
| ready                 | boolean  | Indicates whether the instance is ready.                   |
| restart_count         | integer  | The number of times the instance has been restarted.       |
| version               | string   | The version of the instance.                               |

.instances.metadata

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| resource_version      | string   | The resource version of the instances.                    |


#### .cnative_proc_specs field description

| Field Name            | Type     | Description                                               |
|-----------------------|----------|-----------------------------------------------------------|
| name                  | string   | The name of the process specification (e.g., web).       |
| target_replicas       | integer  | The target number of replicas for the process.            |
| target_status         | string   | The target status for the process (e.g., start).         |
| max_replicas          | integer  | The maximum number of replicas allowed for the process.   |
| resource_limit        | object   | The resource limits for the process.                      |
| resource_requests     | object   | The resource requests for the process.                    |
| plan_name             | string   | The name of the resource plan (e.g., 4C2G).              |
| resource_limit_quota  | object   | The quota limits for CPU and memory resources.           |
| autoscaling           | boolean  | Indicates whether autoscaling is enabled for the process. |
| scaling_config        | object   | The configuration details for autoscaling.                |
| cpu_limit             | string   | The CPU limit for the process (e.g., 4000m).             |
| memory_limit          | string   | The memory limit for the process (e.g., 2048Mi).         |