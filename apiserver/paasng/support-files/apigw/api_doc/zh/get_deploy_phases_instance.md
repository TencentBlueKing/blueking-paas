### 功能描述
获取部署步骤实例

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/{deployment_id}/
```

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   是   |  应用 ID    |
|   module |   string     |   是   |  模块名称，如 "default" |
|   env | string |  是 | 环境名称，可选值 "stag" / "prod" |
|   deployment_id | string |  是 | 部署实例ID(UUID 字符串) |

#### 2、接口参数：
暂无。

### 返回结果示例
```json
[
    {
        "display_name": "准备阶段",
        "type": "preparation",
        "steps": [
            {
                "name": "解析应用进程信息",
                "display_name": "解析应用进程信息",
                "skipped": false,
                "uuid": "34dace83-6fc0-486b-8a20-1a62b7c2a110",
                "status": "successful",
                "start_time": "2024-08-16 10:07:33",
                "complete_time": "2024-08-16 10:07:33"
            },
            {
                "name": "上传仓库代码",
                "display_name": "上传仓库代码",
                "skipped": false,
                "uuid": "1a191578-0b9f-4961-8fef-83cfeb3e9421",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "配置资源实例",
                "display_name": "配置资源实例",
                "skipped": false,
                "uuid": "a346504a-b7d6-4c4b-8db2-537e8f43d87d",
                "status": "successful",
                "start_time": "2024-08-16 10:07:33",
                "complete_time": "2024-08-16 10:07:33"
            }
        ],
        "display_blocks": {
            "source_info": {
                "source_type": "",
                "type": "",
                "trunk_url": null,
                "repo_url": null,
                "source_dir": "",
                "repo_fullname": null,
                "diff_feature": {},
                "linked_to_internal_svn": false,
                "display_name": ""
            },
            "services_info": [
                {
                    "name": "mysql",
                    "display_name": "MySQL",
                    "is_provisioned": true,
                    "service_id": "c8aa4ce5-f5f2-45ef-b6be-d06a0ce703eb",
                    "category_id": 1
                }
            ],
            "prepare_help_docs": [
                {
                    "title": "应用进程概念介绍以及如何使用",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "关于应用进程的简单介绍，内容包含 Procfile",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "应用进程概念介绍以及如何使用",
                    "text": "应用进程概念介绍以及如何使用",
                    "description": "关于应用进程的简单介绍，内容包含 Procfile"
                }
            ]
        },
        "uuid": "9094bfb2-14ab-41bc-a3bc-1794a2c5115d",
        "status": "successful",
        "start_time": "2024-08-16 10:07:33",
        "complete_time": "2024-08-16 10:07:33"
    },
    {
        "display_name": "构建阶段",
        "type": "build",
        "steps": [
            {
                "name": "初始化构建环境",
                "display_name": "初始化构建环境",
                "skipped": false,
                "uuid": "c6220ae7-95e4-4ad8-9ccb-f7cd09689028",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "分析构建方案",
                "display_name": "分析构建方案",
                "skipped": false,
                "uuid": "ae9c4785-5e89-4b65-977d-4180c77ca82b",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "检测构建工具",
                "display_name": "检测构建工具",
                "skipped": false,
                "uuid": "0ef1f2e3-3d90-496e-ab56-a24ece3613a8",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "构建应用",
                "display_name": "构建应用",
                "skipped": false,
                "uuid": "bc9b3bd5-fc2c-4b33-9a14-dba4b14791f9",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "上传镜像",
                "display_name": "上传镜像",
                "skipped": false,
                "uuid": "aefa4786-87af-46c4-8fc5-dc733001dad8",
                "status": null,
                "start_time": null,
                "complete_time": null
            }
        ],
        "display_blocks": {
            "runtime_info": {
                "image": "蓝鲸基础镜像",
                "slugbuilder": null,
                "slugrunner": null,
                "buildpacks": [
                    {
                        "id": 2,
                        "language": "Python",
                        "name": "bk-buildpack-python",
                        "display_name": "Python",
                        "description": "默认 Python 版本为3.10.5"
                    }
                ]
            },
            "build_help_docs": [
                {
                    "title": "如何使用部署前置命令",
                    "location": "http://apps.example.com/bk--docs--center/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/",
                    "name": "如何使用部署前置命令",
                    "text": "如何使用部署前置命令",
                    "description": ""
                }
            ]
        },
        "uuid": "51d9e97f-da21-42dc-a24d-0d20286d9ee5",
        "status": null,
        "start_time": null,
        "complete_time": null
    },
    {
        "display_name": "部署阶段",
        "type": "release",
        "steps": [
            {
                "name": "部署应用",
                "display_name": "部署应用",
                "skipped": false,
                "uuid": "223b64c0-0c6b-478e-a839-3339d75b2838",
                "status": "successful",
                "start_time": "2024-08-16 10:07:33",
                "complete_time": "2024-08-16 10:07:34"
            },
            {
                "name": "执行部署前置命令",
                "display_name": "执行部署前置命令",
                "skipped": false,
                "uuid": "3a9e3144-f300-46f2-90c3-1b2f4097bff1",
                "status": "successful",
                "start_time": "2024-08-16 10:07:34",
                "complete_time": "2024-08-16 10:07:55"
            },
            {
                "name": "检测部署结果",
                "display_name": "检测部署结果",
                "skipped": false,
                "uuid": "3f7e961d-fbb7-4c43-952a-3826513ca426",
                "status": "successful",
                "start_time": "2024-08-16 10:07:34",
                "complete_time": "2024-08-16 10:08:07"
            }
        ],
        "display_blocks": {
            "access_info": {
                "address": "http://apps.example.com/bk--notice/",
                "type": "subpath"
            },
            "release_help_docs": [
                {
                    "title": "配置蓝鲸应用访问入口",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/PaaS/",
                    "name": "配置蓝鲸应用访问入口",
                    "text": "配置蓝鲸应用访问入口",
                    "description": ""
                }
            ]
        },
        "uuid": "4dbe12b7-7a19-4a31-9a21-a080c6e71a08",
        "status": "successful",
        "start_time": "2024-08-16 10:08:07",
        "complete_time": "2024-08-16 10:08:07"
    }
]
```


### 返回结果参数说明

#### Phase 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|-------------|-------------|------------------|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| type | string | 当前阶段类型(可用作标识符) |
| steps | List | 当前阶段包含的步骤 |
| display_blocks | object | 当前阶段的展示模块 |
| uuid | string | UUID |
| status | string | 状态 |
| start_time| string | 开始时间 |
| complete_time | string | 结束时间 |

#### Step 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|-------------|--------------|-----------------|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| name | string | 当前阶段唯一名称 |
| skipped | bool | 是否跳过 |
| uuid | string | uuid |
| status | string | 状态 |
| start_time| string | 开始时间 |
| complete_time | string | 结束时间 |