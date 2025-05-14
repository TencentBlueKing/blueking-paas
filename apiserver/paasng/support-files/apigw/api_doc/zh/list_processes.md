### 功能描述
获取应用环境所有进程与实例信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| ------ | ------ | ------ | ------ |
| app_code | string | 是 | App Code |
| environment | string | 是 | 运行环境 |
| module_name | string | 是 | 模块名称 |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| ------ | ------ | ------ | ------ |
| only_latest_version | boolean | 否 | 是否仅展示最后一个版本的进程 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/envs/prod/processes/list/
```

### 返回结果示例
Status: OK
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

### 返回结果参数说明

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| processes             | object   | 进程信息   |
| instances             | object   | 实例信息   |
| cnative_proc_specs    | object   | 云原生进程配置信息   |


#### .processes 字段说明

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| items                 | array    | 包含进程项的列表                                           |
| extra_infos           | array    | 关于进程的附加信息                                        |
| metadata              | object   | 与进程相关的元数据                                        |

.process.items

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| module_name           | string   | 与进程关联的模块名称                                      |
| name                  | string   | 进程的名称                                                |
| type                  | string   | 进程的类型（例如，web）                                   |
| command               | string   | 进程执行的命令                                            |
| replicas              | integer  | 正在运行的进程副本数量                                    |
| success               | integer  | 成功的副本数量                                            |
| failed                | integer  | 失败的副本数量                                            |
| version               | integer  | 进程的版本                                                |
| cluster_link          | string   | 进程运行所在集群的URL链接                                 |

.process.extra_infos

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| type                  | string   | 进程的类型（例如，web）                                   |
| command               | string   | 进程执行的命令                                            |
| cluster_link          | string   | 进程运行所在集群的URL链接                                 |

.process.metadata

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| resource_version      | string   | 进程的资源版本                                            |


#### .instances

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| items                 | array    | 包含实例项的列表                                           |
| metadata              | object   | 与实例相关的元数据                                        |

.instances.items

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| module_name           | string   | 与实例关联的模块名称                                      |
| name                  | string   | 实例的名称                                                |
| process_type          | string   | 实例的进程类型（例如，web）                               |
| display_name          | string   | 实例的显示名称，通常从实例的唯一标识符派生                |
| image                 | string   | 实例使用的Docker镜像                                      |
| start_time            | string   | 实例的开始时间，采用ISO 8601格式                           |
| state                 | string   | 实例的当前状态（例如，Running）                           |
| state_message         | string   | 描述实例状态的可选信息                                    |
| rich_status           | string   | 实例状态的易读表示                                        |
| ready                 | boolean  | 表示实例是否已准备好                                      |
| restart_count         | integer  | 实例重新启动的次数                                        |
| version               | string   | 实例的版本                                                |

.instances.metadata

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| resource_version      | string   | 实例的资源版本                                            |


#### .cnative_proc_specs 字段说明

| 名称                  | 类型      | 说明                                                      |
|-----------------------|----------|-----------------------------------------------------------|
| name                  | string   | 进程规格的名称（例如，web）                               |
| target_replicas       | integer  | 进程的目标副本数                                          |
| target_status         | string   | 进程的目标状态（例如，start）                             |
| max_replicas          | integer  | 进程允许的最大副本数                                      |
| resource_limit        | object   | 进程的资源限制                                            |
| resource_requests     | object   | 进程的资源请求                                            |
| plan_name             | string   | 资源计划的名称（例如，4C2G）                              |
| resource_limit_quota  | object   | CPU和内存资源的配额限制                                   |
| autoscaling           | boolean  | 表示进程是否启用了自动扩展                                |
| scaling_config        | object   | 自动扩展的配置详情                                        |
| cpu_limit             | string   | 进程的CPU限制（例如，4000m）                              |
| memory_limit          | string   | 进程的内存限制（例如，2048Mi）                            |