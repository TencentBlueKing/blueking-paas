### Description
Get App details

### Request Parameters

#### 1. API Parameters:

| Field | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| limit | number | No | Result quantity |
| offset | number | No | Pagination skip quantity |
| exclude_collaborated | boolean | No | Whether to exclude apps with collaborator permissions, default is not excluded. If true, it means to return only the apps I created |
| include_inactive | boolean | No | Whether to include inactive apps, default is not included |
| language | string | No | APP programming language |
| search_term | string | No | Search keyword |
| source_origin | int | No | Source code origin, currently supports 1 (code repository) and 2 (BlueKing LessCode) |
| type | str | No | Filter by app type, currently supports: default (default), engineless_app (engineless app), bk_plugin (BlueKing plugin) |
| order_by | string | No | Sort, optional values: code, created, last_deployed_date, latest_operated_at, default is ascending, add - for descending, such as -created |

### Request Example
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

### Response Result Example
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

### Response Result Parameter Description

| Field | Type | Description |
| ------ | ------ | ------ |
| count | number | Total count |
| next | string | Next page address |
| previous | string | Previous page address |
| results | array | Result list, including app information |
| extra_data |  object  | Extra information |

.extra_data inter field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| default_app_count  | number | Number of common applications |
| engineless_app_count  | number | Number of external chain applications |       
| cloud_native_app_count  | number | Number of cloud native applications |    
| my_app_count   | number | The number of apps the user created |
| all_app_count  | number | Total application |

.results internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| application | object | BlueKing app information |
| product | object | App market app information |
| marked | boolean | Whether it is marked |
| market_config | object | market disposition |
| migration_status | object | migration status  |

.results.application internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| id | string | App UUID |
| region | string | App region |
| region_name | string | Chinese name corresponding to the region |
| is_active | boolean | Whether the app is active |
| is_deleted | boolean | Whether the app is deleted |
| config_info | object | configration info |
| modules | object | modules |
| last_deployed_date | boolean | App last deployment time |
| owner | string | owner |
| code | string | App Code |
| name | string | App name |
| name_en | string | English App name |
| logo_url | string | App Logo address |
| type | string | Apllication type |
| is_smart_app | boolean | Whether it is a S-mart application |
| is_plugin_app | boolean | Whether it is a plug-in application |
| language | string | App programming language |
| created | string | App creation time |
| updated | string | App modification time |
| deploy_info | object | Deployment information |

.results.application.config_info internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| engine_enabled | boolean | Whether the application engine is used |
| can_create_extra_modules | boolean | Whether could add an extra module |
| confirm_required_when_publish | boolean | Whether the release to the market needs to be confirmed twice |
| market_published | boolean | Whether it has been released to the market |

.results.application.deploy_info internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| stag | object | Stage information |
| prod | object | Production information |

.results.application.deploy_info.stag and prod internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| deployed | bool | Whether it is deployed |
| url | string | Access link |

.results.application.product internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| name | string | App UUID |
| logo | string | App logo address |

.results.application.market_config internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| source_tp_url | string | Source template URL |

.results.application.migration_status internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| status | string | Migration status |
| error_msg | string | Error message |
