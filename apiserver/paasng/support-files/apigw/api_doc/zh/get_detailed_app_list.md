### 功能描述
获取 App 详细信息


### 请求参数

#### 1、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| limit | number | 否 | 结果数量 |
| offset | number | 否 | 翻页跳过数量 |
| exclude_collaborated | boolean | 否 | 是否排除拥有协作者权限的应用，默认不排除。如果为 true，意为只返回我创建的 |
| include_inactive | boolean | 否 | 是否包含已下架应用，默认不包含 |
| language | string | 否 | APP 编程语言 |
| search_term | string | 否 | 搜索关键字 |
| source_origin | int | 否 | 源码来源，目前支持 1（代码仓库）、2（蓝鲸 LessCode） |
| type | str | 否 | 按应用类型筛选，目前支持：default（默认）、engineless_app（无引擎应用）、bk_plugin（蓝鲸插件） |
| order_by | string | 否 | 排序，可选值：code、created、last_deployed_date、latest_operated_at， 默认为升序，前面加 - 后为降序，如 -created |

### 请求示例
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

### 返回结果示例
```json
{
    "count": 62,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/lists/detailed?limit=12&offset=12",
    "previous": null,
    "extra_data": {
        "default_app_count": 7,
        "engineless_app_count": 13,
        "cloud_native_app_count": 42,
        "my_app_count": 1,
        "all_app_count": 62
    },
    "results": [
        {
            "application": {
                "id": "c2166d3e-355b-41aa-9478-e731e3828f41",
                "name": "aaa",
                "region_name": "默认版",
                "logo_url": "http://bkpaas.example.com/static/images/default_logo.png",
                "config_info": {
                    "engine_enabled": true,
                    "can_create_extra_modules": true,
                    "confirm_required_when_publish": false,
                    "market_published": false
                },
                "modules": [
                    {
                        "id": "7c733d25-a3af-47ce-9527-98ea49efbf97",
                        "repo": {
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
                        "repo_auth_info": {},
                        "web_config": {
                            "templated_source_enabled": false,
                            "runtime_type": "buildpack",
                            "build_method": "buildpack",
                            "artifact_type": "image"
                        },
                        "template_display_name": "蓝鲸应用前端开发框架",
                        "source_origin": 2,
                        "clusters": {
                            "prod": {
                                "name": "default-main",
                                "type": "normal",
                                "is_default": true,
                                "bcs_cluster_id": "BCS-K8S-00000",
                                "support_bcs_metrics": false,
                                "ingress_config": {
                                    "sub_path_domains": [
                                        {
                                            "name": "apps.example.com",
                                            "reserved": false,
                                            "https_enabled": false
                                        }
                                    ],
                                    "app_root_domains": [
                                        {
                                            "name": "apps.example.com",
                                            "reserved": false,
                                            "https_enabled": false
                                        }
                                    ],
                                    "frontend_ingress_ip": "",
                                    "default_ingress_domain_tmpl": "%s.apps.example.com",
                                    "port_map": {
                                        "http": 80,
                                        "https": 443
                                    }
                                },
                                "feature_flags": {
                                    "ENABLE_MOUNT_LOG_TO_HOST": true,
                                    "INGRESS_USE_REGEX": true,
                                    "ENABLE_BK_MONITOR": true,
                                    "ENABLE_BK_LOG_COLLECTOR": true,
                                    "ENABLE_AUTOSCALING": false,
                                    "ENABLE_BCS_EGRESS": false
                                }
                            },
                            "stag": {
                                "name": "default-main",
                                "type": "normal",
                                "is_default": true,
                                "bcs_cluster_id": "BCS-K8S-00000",
                                "support_bcs_metrics": false,
                                "ingress_config": {
                                    "sub_path_domains": [
                                        {
                                            "name": "apps.example.com",
                                            "reserved": false,
                                            "https_enabled": false
                                        }
                                    ],
                                    "app_root_domains": [
                                        {
                                            "name": "apps.example.com",
                                            "reserved": false,
                                            "https_enabled": false
                                        }
                                    ],
                                    "frontend_ingress_ip": "",
                                    "default_ingress_domain_tmpl": "%s.apps.example.com",
                                    "port_map": {
                                        "http": 80,
                                        "https": 443
                                    }
                                },
                                "feature_flags": {
                                    "ENABLE_MOUNT_LOG_TO_HOST": true,
                                    "INGRESS_USE_REGEX": true,
                                    "ENABLE_BK_MONITOR": true,
                                    "ENABLE_BK_LOG_COLLECTOR": true,
                                    "ENABLE_AUTOSCALING": false,
                                    "ENABLE_BCS_EGRESS": false
                                }
                            }
                        },
                        "region": "default",
                        "created": "2024-07-10 17:17:36",
                        "updated": "2024-07-10 17:17:36",
                        "owner": "0335cce79c92",
                        "name": "default",
                        "is_default": true,
                        "language": "NodeJS",
                        "source_init_template": "nodejs_bk_magic_vue_spa",
                        "exposed_url_type": 1,
                        "user_preferred_root_domain": null,
                        "last_deployed_date": null,
                        "creator": "0335cce79c92",
                        "application": "c2166d3e-355b-41aa-9478-e731e3828f41"
                    }
                ],
                "deploy_info": {
                    "prod": {
                        "deployed": false,
                        "url": null
                    },
                    "stag": {
                        "deployed": false,
                        "url": null
                    }
                },
                "region": "default",
                "created": "2024-07-10 17:17:36",
                "updated": "2024-07-10 17:17:36",
                "owner": "0335cce79c92",
                "code": "aaa",
                "name_en": "aaa",
                "type": "cloud_native",
                "is_smart_app": false,
                "is_plugin_app": false,
                "language": "NodeJS",
                "creator": "0335cce79c92",
                "is_active": true,
                "is_deleted": false,
                "last_deployed_date": null
            },
            "product": null,
            "marked": false,
            "market_config": {
                "source_tp_url": ""
            },
            "migration_status": {
                "status": "no_need_migration",
                "error_msg": ""
            }
        },
        # ... and more applications
	]
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| count | number | 总数 |
| next | string | 下一页地址 |
| previous | string | 上一页地址 |
| results | array | 结果列表，包含应用信息 |'
| extra_data |  object  | 额外信息 |

.extra_data 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| default_app_count  | number | 普通应用数量 |
| engineless_app_count  | number | 外链应用数量|       
| cloud_native_app_count  | number | 云原生应用数量 |    
| my_app_count   | number |  我创建的应用数量  |
| all_app_count  | number | 应用总数   |

.results 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| application | object | 蓝鲸应用信息 |
| product | object | 应用市场应用信息 |
| marked | boolean | 是否关注 |
| market_config | object | 市场配置  |
| migration_status | object | 迁移状态  |

.results.application 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用 UUID |
| region | string | 应用区域 |
| region_name | string | region 对应的中文名称 |
| is_active | boolean | 应用是否活跃 |
| is_deleted | boolean | 应用是否被删除 |
| config_info | object | 配置信息 |
| modules | object | 模块 |
| last_deployed_date | boolean | 应用最近部署时间 |
| owner | string | 所属人 |
| code | string | 应用 Code |
| name | string | 应用名称 |
| name_en | string | 英文应用名称 |
| logo_url | string | 应用 Logo 地址 |
| type | string | 应用类型 |
| is_smart_app | boolean | 是否为 S-mart 应用 |
| is_plugin_app | boolean | 是否为插件应用 |
| language | string | 应用使用的编程语言 |
| created | string | 应用创建时间 |
| updated | string | 应用修改时间 |
| deploy_info | object | 部署信息 |

.results.application.config_info 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| engine_enabled | boolean | 是否开启了应用引擎 |
| can_create_extra_modules | boolean | 是否能新增模块 |
| confirm_required_when_publish | boolean | 发布到市场时是否需要二次确认 |
| market_published | boolean | 是否已发布到市场 |

.results.application.deploy_info 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| stag | object | 预发布信息 |
| prod | object | 生产信息 |

.results.application.deploy_info.stag 和 prod 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| deployed | bool | 是否部署 |
| url | string | 访问链接 |

.results.application.product 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| name | string | 应用 UUID |
| logo | string | 应用的 logo 地址 |

.results.application.market_config 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| source_tp_url | string | 源模板URL |

.results.application.migration_status 内部字段说明：

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| status | string | 状态 |
| error_msg | string | 错误信息 |