### 功能描述
查询部署任务结果

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称 |
| deployment_id | string | 是 | 部署任务 ID |

#### 2、接口参数：
暂无。

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/{module}/deployments/{deployment_id}/result/
```

### 返回结果示例
```json
{
	"status": "failed",
	"logs": "\nProcfile error: ...",
	"error_detail": "Procfile error: ...",
	"error_tips": {
		"matched_solutions_found": false,
		"possible_reason": "暂时无法找到解决方案，请前往“标准输出日志”检查是否有异常",
		"helpers": [{
			"text": "日志查询",
			"link": "http://bkpaas.example.com/developer-center/apps/appid/default/log?tab=stream"
		}, {
			"text": "去 FAQ 查询试试",
			"link": "https://bk.tencent.com/docs/"
		}]
	}
}
```

### 返回结果参数说明

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| status | string | 是 | 部署状态 |
| logs | string | 是 | 部署日志, 纯文本 |
| error_detail | string | 是 | 错误详情 |
| error_tips.matched_solutions_found | boolean | 是 | 是否有匹配的 tips |
| error_tips.possible_reason | string | 是 | 可能导致部署错误的原因 |
| error_tips.helpers | object | 是 | 辅助信息，包含文本和链接 |