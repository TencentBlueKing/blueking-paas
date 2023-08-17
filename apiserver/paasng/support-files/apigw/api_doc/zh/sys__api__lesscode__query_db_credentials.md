### 功能描述
注册资源的简单描述

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：

| 参数名称    | 参数类型 | 是否必填 | 参数说明                                                         |
| ----------- | -------- | -------- | ---------------------------------------------------------------- |
| app_code    | string   | 是       | 应用ID(app id)，可以通过 蓝鲸开发者中心 -> 应用基本设置 -> 基本信息 -> 鉴权信息 获取 |
| app_secret  | string   | 否       | 安全秘钥(app secret)，可以通过 蓝鲸开发者中心 -> 应用基本设置 -> 基本信息 -> 鉴权信息 获取 |

### 请求示例
```python
from bkapigw.paasv3.shortcuts import get_client_by_request
client = get_client_by_request(request)
# 填充参数
kwargs = {

}
result = client.api.api_test(kwargs)
```

### 返回结果示例
```json
# 内部版
{
    "credentials": {
        "GCS_MYSQL_HOST": "--",
        "GCS_MYSQL_PORT": --,
        "GCS_MYSQL_NAME": "--",
        "GCS_MYSQL_USER": "--",
        "GCS_MYSQL_PASSWORD": "--"
    }
}

# 企业版
{
    "credentials": {
        "MYSQL_HOST": "--",
        "MYSQL_PORT": --,
        "MYSQL_NAME": "--",
        "MYSQL_USER": "--",
        "MYSQL_PASSWORD": "--"
    }
}

# 失败返回
{
    "code": "CANNOT_READ_INSTANCE_INFO",
    "detail": "读取增强服务实例信息失败: 无法获取到有效的配置信息."
}

```

### 返回结果参数说明

| 参数名称          | 参数类型 | 参数说明                   |
| ----------------- | -------- | -------------------------- |
| credentials       | dict     | 数据库连接信息             |
| GCS_MYSQL_HOST    | string   | 数据库主机地址             |
| GCS_MYSQL_PORT    | int      | 数据库端口                 |
| GCS_MYSQL_NAME    | string   | 数据库名称                 |
| GCS_MYSQL_USER    | string   | 数据库用户名               |
| GCS_MYSQL_PASSWORD| string   | 数据库密码                 |
| MYSQL_HOST        | string   | 数据库主机地址（企业版）   |
| MYSQL_PORT        | int      | 数据库端口（企业版）       |
| MYSQL_NAME        | string   | 数据库名称（企业版）       |
| MYSQL_USER        | string   | 数据库用户名（企业版）     |
| MYSQL_PASSWORD    | string   | 数据库密码（企业版）       |
| code              | string   | 错误码                     |
| detail            | string   | 错误详情                   |