### Resource Description
get deploy phases for deployment instance

### Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"bk_app_code": "***", "bk_app_secret": "***", "access_token": "***"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/envs/{env}/get_deploy_phases/{deployment_id}/
```

### Path parameter

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   |  string |yes| App ID, e.g. "Monitor" |
| module   |  string | yes      | Module name, such as "default"|
| env   |  string | yes      | Environment name, e.g. "Stag,""prod"|
|   deployment_id | string |  是 | the id field of deployment instance |


### Response
```json
[{
	"display_name": "Preparation Phase",
	"type": "preparation",
	"steps": [{
		"name": "解析应用进程信息",
		"display_name": "Parse app process"
	}, {
		"name": "上传仓库代码",
		"display_name": "Upload repository code"
	}, {
		"name": "配置资源实例",
		"display_name": "Config resource instance"
	}]
}, {
	"display_name": "Build Phase",
	"type": "build",
	"steps": [{
		"name": "下载代码",
		"display_name": "Downloading code"
	}, {
		"name": "加载缓存",
		"display_name": "Restoring cache"
	}, {
		"name": "构建应用",
		"display_name": "Building Applications"
	}, {
		"name": "检测进程类型",
		"display_name": "Discover process types"
	}, {
		"name": "制作打包构件",
		"display_name": "Making slug package"
	}, {
		"name": "上传缓存",
		"display_name": "Upload Cache"
	}]
}, {
	"display_name": "Deploy Phase",
	"type": "release",
	"steps": [{
		"name": "执行部署前置命令",
		"display_name": "Execute Pre-release cmd"
	}, {
		"name": "部署应用",
		"display_name": "Deploying the app"
	}, {
		"name": "检测部署结果",
		"display_name": "View Deploy results"
	}]
}]
```

### Description of the Response

#### Description of the fields of the DeployPhase object
|   Field   |    Type  |    Description     |
|---|---|---|---|
| display_name | string | The display name of DeployPhase object |
| type | string | The type of DeployPhase object |
| steps | List | Steps included in the DeployPhase |


#### Description of the fields of the DeployStep object
|   Field   |    Type  |    Description     |
|---|---|---|---|
| display_name | string | The display name of DeployStep object |
| name | string | The unique name of DeployStep object |
