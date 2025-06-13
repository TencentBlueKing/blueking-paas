### 功能描述  
获取应用模块的运行时概览信息（包括代码仓库相关信息）  

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
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{}' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/runtime/overview
```  

### 返回结果示例  
```json
{
    "repo": {
        "source_type": "github",
        "type": "github",
        "trunk_url": "http://git.example.com/app-test.git",
        "repo_url": "http://git.example.com/app-test.git",
        "source_dir": "",
        "repo_fullname": "app-test",
        "diff_feature": {
            "method": "external",
            "enabled": true
        }
    }
}
```  

### 返回结果参数说明  
| 字段 |   类型 |  是否必填 | 描述 |  
| ------ | ------ | ------ | ------ |  
| repo | dict | 是 | 代码仓库相关信息 |  

**repo 字段说明：**  
| 字段 |   类型 |  是否必填 | 描述 |  
| ------ | ------ | ------ | ------ |  
| source_type | string | 是 | 代码来源类型（如 "github"） |  
| type | string | 是 | 仓库类型（通常与 source_type 相同） |  
| trunk_url | string | 是 | 主分支 URL |  
| repo_url | string | 是 | 仓库 URL |  
| source_dir | string | 是 | 源代码目录 |  
| repo_fullname | string | 是 | 仓库完整名称（如 "app-test"） |  
| diff_feature | dict | 是 | 差异对比功能配置 |  