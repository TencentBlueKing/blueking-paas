### 描述

获取应用环境所有进程与实例信息

### 输入参数

| 参数名称 | 参数位置 | 类型 | 必选 | 描述 |
|------|--------|------| :------: |-------------|
| app_code | `path` | string | 是 | App Code |
| environment | `path` | string | 是 | 运行环境 |
| module_name | `path` | string | 是 | 模块名称 |
| only_latest_version | `query` | boolean |  | 是否仅展示最后一个版本的进程 |

### 所有响应
| 状态码 | 状态 | 描述 |
|------|--------|-------------|
| 200 | OK | 获取成功 |
| 400 | Bad Request | 错误信息 |

### 响应

#### 200 - 获取成功
Status: OK

##### Schema

ListProcessesOKBody

#### 400 - 错误信息
Status: Bad Request

##### Schema

ListProcessesBadRequestBody

##### 内联模型

**ListProcessesBadRequestBody**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| code | string (formatted integer)|  | 错误代码 |  |
| detail | string|  | 错误详情 |  |
| fields_detail | interface{}|  | 仅当错误类型为 `VALIDATION_ERROR` 时存在，内容为各字段错误详情 |  |



**ListProcessesOKBody**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| instances | ListProcessesOKBodyInstances|  |  |  |
| process_packages | []ListProcessesOKBodyProcessPackagesItems0|  | 进程在平台的配置状态 |  |
| processes | ListProcessesOKBodyProcesses|  |  |  |



**ListProcessesOKBodyInstances**


> 所有实例状态



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| items | []ListProcessesOKBodyInstancesItemsItems0|  |  |  |
| metadata | ListProcessesOKBodyInstancesMetadata|  |  |  |



**ListProcessesOKBodyInstancesItemsItems0**


> 对象类型为 instance 时的结构，仅做说明用，内容任通过 `object` 字段提供。



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| display_name | string|  | 用于展示的短名字 |  |
| name | string|  | 实例名称 |  |
| process_type | string|  | 进程类型名称 |  |
| ready | boolean|  | 实例是否就绪 |  |
| start_time | string|  | 实例启动时间 |  |
| state | string|  | 实例状态，可能的值："Running" / "Starting" 等 |  |
| version | integer|  | 实例 release 版本号，客户端可使用该值与 Process 进行对比，判断实例是否为最新版 |  |



**ListProcessesOKBodyInstancesMetadata**


> 元信息



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| resource_version | string|  | 本地资源版本号，可用于 watch 请求的 rv_inst 参数 |  |



**ListProcessesOKBodyProcessPackagesItems0**


> 进程配置状态



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| max_replicas | integer|  | 后台允许的最大实例数 |  |
| name | string|  | 进程类型，如 "web" |  |
| resource_limit | string|  | CPU 与内存限制信息 |  |
| target_replicas | integer|  | 用户设置的目标副本数 |  |
| target_status | integer|  | 用户设置的目标状态 |  |



**ListProcessesOKBodyProcesses**


> 进程当前状态



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| extra_infos | []ListProcessesOKBodyProcessesExtraInfosItems0|  |  |  |
| items | []ListProcessesOKBodyProcessesItemsItems0|  |  |  |
| metadata | ListProcessesOKBodyProcessesMetadata|  |  |  |



**ListProcessesOKBodyProcessesExtraInfosItems0**



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| cluster_link | string|  | 进程集群内访问地址 |  |
| command | string|  | 进程命令 |  |
| type | string|  | 进程类型 |  |



**ListProcessesOKBodyProcessesItemsItems0**


> 对象类型为 process 时的结构，仅做说明用，内容任通过 `object` 字段提供。



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| failed | integer|  | 错误（失败）实例数 |  |
| name | string|  | 进程名称 |  |
| replicas | integer|  | 进程设置（预期）实例数 |  |
| success | integer|  | 正常实例数 |  |
| type | string|  | 进程类型 |  |
| version | integer|  | 进程 release 版本号 |  |



**ListProcessesOKBodyProcessesMetadata**


> 元信息



**Properties**

| 名称 | 类型 | 必选 | 描述 | 示例 |
|------|------|:--------:|-------------|---------|
| resource_version | string|  | 本地资源版本号，可用于 watch 请求的 rv_proc 参数 |  |