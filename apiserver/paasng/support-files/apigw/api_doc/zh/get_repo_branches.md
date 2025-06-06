### 功能描述  
获取应用模块的代码仓库分支列表  

### 请求参数  

#### 1、路径参数：  
|   参数名称   |    参数类型  |  必须  |     参数说明     |  
| ------------ | ------------ | ------ | ---------------- |  
| app_code   | string | 是 | 应用 ID，如 "appid1" |  
| module   | string | 是 | 模块名称，如 "default" |  

#### 2、接口参数：  
暂无。  

### 请求示例  
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{}' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/repo/branches/
```  

### 返回结果示例  
```json
{
    "results": [
        {
            "name": "master",
            "type": "branch",
            "display_type": "branch",
            "revision": "31736e690ba0bfa7a81d3730ed6544b3566b3f19",
            "url": "http://git.example.com/app-test.git",
            "last_update": "2024-09-10 16:48:24",
            "message": "init repo",
            "extra": {}
        }
    ]
}
```  

### 返回结果参数说明  
| 字段 |   类型 |  是否必填 | 描述 |  
| ------ | ------ | ------ | ------ |  
| results | list | 是 | 分支列表 |  

**results 字段说明：**  
| 字段 |   类型 |  是否必填 | 描述 |  
| ------ | ------ | ------ | ------ |  
| name | string | 是 | 分支名称 |  
| type | string | 是 | 分支类型（branch/tag） |  
| display_type | string | 是 | 显示类型（branch/tag） |  
| revision | string | 是 | 分支的最新提交哈希 |  
| url | string | 是 | 仓库 URL |  
| last_update | string | 是 | 最后更新时间 |  
| message | string | 是 | 最后提交的提交信息 |  
| extra | dict | 是 | 额外信息 |