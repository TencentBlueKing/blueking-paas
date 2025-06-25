### 功能描述  
更新或创建应用的环境变量的值  

### 请求参数  

#### 1、路径参数：  
|   参数名称   |    参数类型  |  必须  |     参数说明     |  
| ------------ | ------------ | ------ | ---------------- |  
| app_code   | string | 是 | 应用 ID，如 "appid1" |  
| module   | string | 是 | 模块名称，如 "default" |  
| config_key | string | 是 | 配置变量名，如 "KEY1" |  

#### 2、接口参数：  
|   参数名称   |    参数类型  |  必须  |     参数说明     |  
| ------------ | ------------ | ------ | ---------------- |  
| environment_name   | string | 是 | 环境，预发布环境：stag、生产环境：prod |  
| value   | string | 是 | 环境变量的值 |  
| description | string | 是 | 环境变量描述 |  

### 请求示例  
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{    "environment_name": "stag",    "value": "0.0.1",    "description": "d0.0.1版本"}' --insecure http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/config_vars/KEY1/
```  

### 返回结果示例  

**状态码说明：**  
- **201**：配置变量创建或更新成功