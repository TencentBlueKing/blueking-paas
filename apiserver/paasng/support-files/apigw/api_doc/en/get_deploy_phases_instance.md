### Description
Get deployment step instances

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/{deployment_id}/
```

### Request Parameters

#### 1. Path Parameters:

|   Parameter Name   |    Parameter Type  |  Required  |     Parameter Description     |
| ------------ | ------------ | ------ | ---------------- |
|   app_code   |   string     |   Yes   |  Application ID    |
|   module |   string     |   Yes   |  Module name, e.g. "default" |
|   env | string |  Yes | Environment name, available values "stag" / "prod" |
|   deployment_id | string |  Yes | Deployment instance ID (UUID string) |

#### 2. API Parameters:
None.

### Response Result Example
```json
[
    {
        "display_name": "Preparation Stage",
        "type": "preparation",
        "steps": [
            {
                "name": "Parse Application Process Information",
                "display_name": "Parse Application Process Information",
                "skipped": false,
                "uuid": "34dace83-6fc0-486b-8a20-1a62b7c2a110",
                "status": "successful",
                "start_time": "2024-08-16 10:07:33",
                "complete_time": "2024-08-16 10:07:33"
            },
            {
                "name": "Upload Repository Code",
                "display_name": "Upload Repository Code",
                "skipped": false,
                "uuid": "1a191578-0b9f-4961-8fef-83cfeb3e9421",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "Configure Resource Instances",
                "display_name": "Configure Resource Instances",
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
                    "title": "Introduction to Application Process Concepts and How to Use",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "A brief introduction to application processes, including content on Procfile",
                    "link": "http://apps.example.com/bk--docs--center/markdown/",
                    "name": "Introduction to Application Process Concepts and How to Use",
                    "text": "Introduction to Application Process Concepts and How to Use",
                    "description": "A brief introduction to application processes, including content on Procfile"
                }
            ]
        },
        "uuid": "9094bfb2-14ab-41bc-a3bc-1794a2c5115d",
        "status": "successful",
        "start_time": "2024-08-16 10:07:33",
        "complete_time": "2024-08-16 10:07:33"
    },
    {
        "display_name": "Build Stage",
        "type": "build",
        "steps": [
            {
                "name": "Initialize Build Environment",
                "display_name": "Initialize Build Environment",
                "skipped": false,
                "uuid": "c6220ae7-95e4-4ad8-9ccb-f7cd09689028",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "Analyze Build Plan",
                "display_name": "Analyze Build Plan",
                "skipped": false,
                "uuid": "ae9c4785-5e89-4b65-977d-4180c77ca82b",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "Check Build Tools",
                "display_name": "Check Build Tools",
                "skipped": false,
                "uuid": "0ef1f2e3-3d90-496e-ab56-a24ece3613a8",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "Build Application",
                "display_name": "Build Application",
                "skipped": false,
                "uuid": "bc9b3bd5-fc2c-4b33-9a14-dba4b14791f9",
                "status": null,
                "start_time": null,
                "complete_time": null
            },
            {
                "name": "Upload Image",
                "display_name": "Upload Image",
                "skipped": false,
                "uuid": "aefa4786-87af-46c4-8fc5-dc733001dad8",
                "status": null,
                "start_time": null,
                "complete_time": null
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
                    "location": "http://apps.example.com/bk--docs--center/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/",
                    "name": "How to Use Pre-Deployment Commands",
                    "text": "How to Use Pre-Deployment Commands",
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
        "display_name": "Release Stage",
        "type": "release",
        "steps": [
            {
                "name": "Deploy Application",
                "display_name": "Deploy Application",
                "skipped": false,
                "uuid": "223b64c0-0c6b-478e-a839-3339d75b2838",
                "status": "successful",
                "start_time": "2024-08-16 10:07:33",
                "complete_time": "2024-08-16 10:07:34"
            },
            {
                "name": "Execute Pre-Deployment Commands",
                "display_name": "Execute Pre-Deployment Commands",
                "skipped": false,
                "uuid": "3a9e3144-f300-46f2-90c3-1b2f4097bff1",
                "status": "successful",
                "start_time": "2024-08-16 10:07:34",
                "complete_time": "2024-08-16 10:07:55"
            },
            {
                "name": "Check Deployment Results",
                "display_name": "Check Deployment Results",
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
                    "title": "Configure BlueKing Application Access Entry",
                    "location": "http://apps.example.com/bk--docs--center/markdown/",
                    "short_description": "",
                    "link": "http://apps.example.com/bk--docs--center/markdown/PaaS/",
                    "name": "Configure BlueKing Application Access Entry",
                    "text": "Configure BlueKing Application Access Entry",
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

### Response Result Parameter Description

#### Phase Object Field Description
|   Parameter Name   |    Parameter Type  |     Parameter Description     |
|--------------------|--------------------|-------------------------------|
| display_name | string | Display name of the current phase (changes with i18n) |
| type | string | Type of the current phase (can be used as an identifier) |
| steps | List | Steps included in the current phase |
| display_blocks | object | Display blocks of the current phase |
| uuid | string | UUID |
| status | string | Status |
| start_time| string | Start time |
| complete_time | string | Complete time |

#### Step Object Field Description
|   Parameter Name   |    Parameter Type  |     Parameter Description     |
|--------------------|--------------------|-------------------------------|
| display_name | string | Display name of the current step (changes with i18n) |
| name | string | Unique name of the current step |
| skipped | bool | Whether skipped this step |
| uuid | string | UUID |
| status | string | Status |
| start_time| string | Start time |
| complete_time | string | Complete time |