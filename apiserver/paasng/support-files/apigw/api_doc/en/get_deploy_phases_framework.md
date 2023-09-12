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
[{
        "display_name": "Preparation Phase",
        "type": "preparation",
        "steps": [{
            "name": "Parse application process information",
            "display_name": "Parse application process information"
        }, {
            "name": "Upload repository code",
            "display_name": "Upload repository code"
        }, {
            "name": "Configure resource instance",
            "display_name": "Configure resource instance"
        }]
    },
    {
        "display_name": "Build Phase",
        "type": "build",
        "steps": [{
            "name": "Initialize build environment",
            "display_name": "Initialize build environment"
        }, {
            "name": "Detect build tools",
            "display_name": "Detect build tools"
        }, {
            "name": "Analyze build scheme",
            "display_name": "Analyze build scheme"
        }, {
            "name": "Call pre-compile",
            "display_name": "Call pre-compile"
        }, {
            "name": "Build application",
            "display_name": "Build application"
        }, {
            "name": "Call post-compile",
            "display_name": "Call post-compile"
        }, {
            "name": "Generate build results",
            "display_name": "Generate build results"
        }, {
            "name": "Clean up build environment",
            "display_name": "Clean up build environment"
        }]
    },
    {
        "display_name": "Deployment Phase",
        "type": "release",
        "steps": [{
            "name": "Execute pre-deployment command",
            "display_name": "Execute pre-deployment command"
        }, {
            "name": "Deploy application",
            "display_name": "Deploy application"
        }, {
            "name": "Detect deployment result",
            "display_name": "Detect deployment result"
        }]
    ]
```

### Response Parameter Description

#### Phase Object Field Description
|   Parameter Name   |    Parameter Type  |     Description     |
|---|---|---|---|
| display_name | string | Display name of the current phase (changes with i18n) |
| type | string | Type of the current phase (can be used as an identifier) |
| steps | List | Steps included in the current phase |

#### Step Object Field Description
|   Parameter Name   |    Parameter Type  |     Description     |
|---|---|---|---|
| display_name | string | Display name of the current phase (changes with i18n) |
| name | string | Unique name of the current phase |