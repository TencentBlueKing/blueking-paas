### Description
Get deployment steps (structure)

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | Yes | Application ID |
| module   | string | Yes | Module name, e.g. "default" |
| env | string | Yes | Environment name, available values: "stag" / "prod" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/
```

### Response Example
```json
[
    {
        "display_name": "Preparation Stage",
        "type": "preparation",
        "steps": [
            {
                "name": "Parse Application Process Information",
                "display_name": "Parse Application Process Information",
                "skipped": false
            },
            {
                "name": "Upload Repository Code",
                "display_name": "Upload Repository Code",
                "skipped": false
            },
            {
                "name": "Configure Resource Instances",
                "display_name": "Configure Resource Instances",
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
                    "title": "Introduction to Application Process Concepts and How to Use",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "A brief introduction to application processes, including content on Procfile",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "Introduction to Application Process Concepts and How to Use",
                    "text": "Introduction to Application Process Concepts and How to Use",
                    "description": "A brief introduction to application processes, including content on Procfile"
                }
            ]
        }
    },
    {
        "display_name": "Build Stage",
        "type": "build",
        "steps": [
            {
                "name": "Initialize Build Environment",
                "display_name": "Initialize Build Environment",
                "skipped": false
            },
            {
                "name": "Analyze Build Plan",
                "display_name": "Analyze Build Plan",
                "skipped": false
            },
            {
                "name": "Check Build Tools",
                "display_name": "Check Build Tools",
                "skipped": false
            },
            {
                "name": "Build Application",
                "display_name": "Build Application",
                "skipped": false
            },
            {
                "name": "Upload Image",
                "display_name": "Upload Image",
                "skipped": false
            }
        ],
        "display_blocks": {
            "runtime_info": {
                "image": "BlueKing Base Image",
                "slugbuilder": null,
                "slugrunner": null,
                "buildpacks": [
                    {
                        "id": 2,
                        "language": "Python",
                        "name": "bk-buildpack-python",
                        "display_name": "Python",
                        "description": "The default Python version is 3.10.5"
                    }
                ]
            },
            "build_help_docs": [
                {
                    "title": "How to Use Pre-Deployment Commands",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "How to Use Pre-Deployment Commands",
                    "text": "How to Use Pre-Deployment Commands",
                    "description": ""
                }
            ]
        }
    },
    {
        "display_name": "Release Stage",
        "type": "release",
        "steps": [
            {
                "name": "Deploy Application",
                "display_name": "Deploy Application",
                "skipped": false
            },
            {
                "name": "Execute Pre-Deployment Commands",
                "display_name": "Execute Pre-Deployment Commands",
                "skipped": false
            },
            {
                "name": "Check Deployment Results",
                "display_name": "Check Deployment Results",
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
                    "title": "Configure BlueKing Application Access Entry",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "Configure BlueKing Application Access Entry",
                    "text": "Configure BlueKing Application Access Entry",
                    "description": ""
                }
            ]
        }
    }
]

```

### Response Parameter Description

#### Phase Object Field Description
|   Parameter Name   |    Parameter Type  |     Description     |
|--------------------|--------------------|---------------------|
| display_name | string | Display name of the current phase (changes with i18n) |
| type | string | Type of the current phase (can be used as an identifier) |
| steps | List | Steps included in the current phase |
| display_blocks | object | Display blocks of the current phase |

#### Step Object Field Description
|   Parameter Name   |    Parameter Type  |     Description     |
|--------------------|--------------------|---------------------|
| display_name | string | Display name of the current phase (changes with i18n) |
| name | string | Unique name of the current phase |
| skipped | bool | whether skipped this step |