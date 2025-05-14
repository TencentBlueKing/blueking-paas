### 功能描述
获取部署步骤(结构体)

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/
```

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
                "skipped": false
            },
            {
                "name": "上传仓库代码",
                "display_name": "上传仓库代码",
                "skipped": false
            },
            {
                "name": "配置资源实例",
                "display_name": "配置资源实例",
                "skipped": false
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
        }
    },
    {
        "display_name": "构建阶段",
        "type": "build",
        "steps": [
            {
                "name": "初始化构建环境",
                "display_name": "初始化构建环境",
                "skipped": false
            },
            {
                "name": "分析构建方案",
                "display_name": "分析构建方案",
                "skipped": false
            },
            {
                "name": "检测构建工具",
                "display_name": "检测构建工具",
                "skipped": false
            },
            {
                "name": "构建应用",
                "display_name": "构建应用",
                "skipped": false
            },
            {
                "name": "上传镜像",
                "display_name": "上传镜像",
                "skipped": false
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
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "如何使用部署前置命令",
                    "text": "如何使用部署前置命令",
                    "description": ""
                }
            ]
        }
    },
    {
        "display_name": "部署阶段",
        "type": "release",
        "steps": [
            {
                "name": "部署应用",
                "display_name": "部署应用",
                "skipped": false
            },
            {
                "name": "执行部署前置命令",
                "display_name": "执行部署前置命令",
                "skipped": false
            },
            {
                "name": "检测部署结果",
                "display_name": "检测部署结果",
                "skipped": false
            }
        ],
        "display_blocks": {
            "access_info": {
                "address": "http://apps.example.com/example",
                "type": "subpath"
            },
            "release_help_docs": [
                {
                    "title": "配置蓝鲸应用访问入口",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "配置蓝鲸应用访问入口",
                    "text": "配置蓝鲸应用访问入口",
                    "description": ""
                }
            ]
        }
    }
]
```

### 返回结果参数说明

#### Phase 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|-------------|--------------|-----------------|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| type | string | 当前阶段类型(可用作标识符) |
| steps | List | 当前阶段包含的步骤 |
| display_blocks | object | 当前阶段的展示模块 |

#### Step 对象各字段说明
|   参数名称   |    参数类型  |     参数说明     |
|-------------|-------------|------------------|
| display_name | string | 当前阶段的展示用名称(会随着 i18n 改变) |
| name | string | 当前阶段唯一名称 |
| skipped | bool | 是否跳过 |