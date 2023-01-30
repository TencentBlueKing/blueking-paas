### Description

Get all process and instance information of the application environment

### Input parameters

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  `string` |yes| App ID, e.g. "Monitor" |
| module   |  `string` | yes      | Module name, such as "default"|
| env   |  `string` | yes      | Environment name, e.g. "Stag,""prod"|
| only_latest_version | `query` | boolean |  | whether to show only the last version of the process |

### All responses
| Status Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Get success |
| 400 | Bad Request | Error message |

### 响应

#### 200 - OK
Status: OK

##### Schema

ListProcessesOKBody

#### 400 - Bad Request
Status: Bad Request

##### Schema

ListProcessesBadRequestBody

##### 内联模型

**ListProcessesBadRequestBody**



**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| code | string (formatted integer)| | error code | |
| detail | string| | Error details | |
| fields_detail | interface{}| | Only exists when the error type is `VALIDATION_ERROR`, the content is the error details of each field | |

**ListProcessesOKBody**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| instances | ListProcessesOKBodyInstances|  |  |  |
| process_packages | []ListProcessesOKBodyProcessPackagesItems0|  | 进程在平台的配置状态 |  |
| processes | ListProcessesOKBodyProcesses|  |  |  |



**ListProcessesOKBodyInstances**
> All instance states


**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| items | []ListProcessesOKBodyInstancesItemsItems0|  |  |  |
| metadata | ListProcessesOKBodyInstancesMetadata|  |  |  |



**ListProcessesOKBodyInstancesItemsItems0**
> The structure when the object type is instance, for illustration only

**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| display_name | string| | short name for display | |
| name | string| | instance name | |
| process_type | string| | Process type name | |
| ready | boolean| | Whether the instance is ready | |
| start_time | string| | instance start time | |
| state | string| | instance state, possible values: "Running" / "Starting" etc | |
| version | integer| | The instance release version number, the client can use this value to compare with Process to determine whether the instance is the latest version | |



**ListProcessesOKBodyInstancesMetadata**
**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| resource_version | string| | The local resource version number, which can be used in the rv_inst parameter of the watch request | |


**ListProcessesOKBodyProcessPackagesItems0**
> Process configuration status

**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| max_replicas | integer| | Maximum number of instances allowed in the background | |
| name | string| | Process type, such as "web" | |
| resource_limit | string| | CPU and memory limit information | |
| target_replicas | integer| | The number of target replicas set by the user | |
| target_status | integer| | target status set by the user | |


**ListProcessesOKBodyProcesses**
> current state of the process

**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| extra_infos | []ListProcessesOKBodyProcessesExtraInfosItems0| | | |
| items | []ListProcessesOKBodyProcessesItemsItems0| | | |
| metadata | ListProcessesOKBodyProcessesMetadata| | | |

**ListProcessesOKBodyProcessesExtraInfosItems0**

**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| cluster_link | string| | Access address in the process cluster | |
| command | string| | Process command | |
| type | string| | Process type | |

**ListProcessesOKBodyProcessesItemsItems0**

> The structure when the object type is process, for illustration only

**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| failed | integer| | Number of false (failed) instances | |
| name | string| | Process name | |
| replicas | integer| | Process setting (expected) number of instances | |
| success | integer| | number of normal instances | |
| type | string| | Process type | |
| version | integer| | Process release version number | |


**ListProcessesOKBodyProcessesMetadata**
**Properties**

| Name | Type | Required | Description | Example |
|------|------|:------------:|-------------|---------|
| resource_version | string| | The local resource version number, which can be used in the rv_proc parameter of the watch request | |
