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
暂无。

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/envs/prod/processes/list/
```

### 返回结果示例
Status: OK

### 返回结果参数说明

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| instances | ListProcessesOKBodyInstances | 是 | 所有实例状态 |
| process_packages | []ListProcessesOKBodyProcessPackagesItems0 | 是 | 进程在平台的配置状态 |
| processes | ListProcessesOKBodyProcesses | 是 | 进程当前状态 |

**ListProcessesOKBodyInstancesItemsItems0**
| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| display_name | string | 是 | 用于展示的短名字 |
| name | string | 是 | 实例名称 |
| process_type | string | 是 | 进程类型名称 |
| ready | boolean | 是 | 实例是否就绪 |
| start_time | string | 是 | 实例启动时间 |
| state | string | 是 | 实例状态，可能的值："Running" / "Starting" 等 |
| version | integer | 是 | 实例 release 版本号，客户端可使用该值与 Process 进行对比，判断实例是否为最新版 |

**ListProcessesOKBodyProcessPackagesItems0**
| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| max_replicas | integer | 是 | 后台允许的最大实例数 |
| name | string | 是 | 进程类型，如 "web" |
| resource_limit | string | 是 | CPU 与内存限制信息 |
| target_replicas | integer | 是 | 用户设置的目标副本数 |
| target_status | integer | 是 | 用户设置的目标状态 |

**ListProcessesOKBodyProcessesItemsItems0**
| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| failed | integer | 是 | 错误（失败）实例数 |
| name | string | 是 | 进程名称 |
| replicas | integer | 是 | 进程设置（预期）实例数 |
| success | integer | 是 | 正常实例数 |
| type | string | 是 | 进程类型 |
| version | integer | 是 | 进程 release 版本号 |