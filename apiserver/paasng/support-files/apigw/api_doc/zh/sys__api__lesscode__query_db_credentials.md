### 功能描述
查询数据库增强服务的 credential 信息

当前 API 默认值提供给蓝鲸运维开发平台（应用ID：bk_lesscode）

### 请求参数

#### 1、路径参数：

| 参数名称  | 参数类型 | 必须 | 参数说明         |
| --------- | -------- | ---- | ---------------- |
| app_code  | string   | 是   | 应用 ID          |
| module    | string   | 是   | 模块名称         |
| env       | string   | 是   | 环境，如 "prod"  |

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "visual-layout", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/modules/default/envs/prod/lesscode/query_db_credentials
```

### 返回结果示例

#### 正常返回

```json
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}
```

| 参数名称          | 参数类型 | 参数说明                   |
| -----------------| -------- | ------------------------- |
| credentials      | dict     | 数据库连接信息             |
| MYSQL_HOST       | string   | 数据库主机地址             |
| MYSQL_PORT       | int      | 数据库端口                 |
| MYSQL_NAME       | string   | 数据库名称                 |
| MYSQL_USER       | string   | 数据库用户名               |
| MYSQL_PASSWORD   | string   | 数据库密码                 |

#### 异常返回

```json
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "读取增强服务实例信息失败: 无法获取到有效的配置信息."
}
```

| 参数名称          | 参数类型 | 参数说明                   |
| ----------------- | -------- | ------------------------ |
| code              | string   | 错误码                    |
| detail            | string   | 错误详情                  |