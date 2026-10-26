### 功能描述

以应用身份查询 AI Agent 应用指定环境的进程与进程实例**实际状态**（用于企微 wxaibot 进程巡检）。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| module | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| release_id | string | 否 | 用于过滤实例的发布 ID |

### 请求示例

```
curl -X GET -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/envs/stag/processes/list/
```

### 返回结果示例

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
    "process_packages": [
        {
            "name": "web",
            "target_replicas": 1,
            "target_status": "start"
        }
    ]
}
```

### 返回结果参数说明

| 名称 | 类型 | 说明 |
| ------ | ------ | ------ |
| processes | object | 进程实际状态信息 |
| instances | object | 进程实例实际状态信息 |
| process_packages | array | 进程配置信息（期望副本数、期望状态等） |

各字段明细与用户态接口 `list_processes` 完全一致。
