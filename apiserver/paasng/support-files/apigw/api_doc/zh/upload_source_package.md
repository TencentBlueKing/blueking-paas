### 功能描述
上传源码包至平台

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| code   | string | 是 | 代码 |
| module_name   | string | 是 | 模块名称 |

#### 2、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| package | file | 是 | 源码包文件 |
| allow_overwrite | boolean | 否 | 是否允许覆盖原有的源码包 |

### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### 返回结果示例
```json
{
  "version": "v1",
  "package_name": "tmpcvml_dsm.tar.gz",
  "package_size": "4586",
  "sha256_signature": null,
  "updated": "2020-08-24 17:15:51",
  "created": "2020-08-24 17:15:51"
}
```

### 返回结果参数说明

| 字段 |   类型 |  描述 |
| ------ | ------ | ------ |
| version | string | 版本信息 |
| package_name | string | 源码包名称 |
| package_size | string | 源码包大小 |
| sha256_signature | string | sha256数字签名 |
| updated | string | 更新时间 |
| created | string | 创建时间 |