### 功能描述
根据下载链接上传源码包至平台

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| code     | string   | 是   | 应用 ID  |
| module_name | string | 是 | 模块名称 |

#### 2、接口参数：

| 字段            | 类型    | 是否必填 | 描述                   |
| --------------- | ------- | -------- | ---------------------- |
| package_url     | string  | 是       | 源码包下载路径         |
| version         | string  | 否       | 源码包版本号           |
| allow_overwrite | boolean | 否       | 是否允许覆盖原有的源码包 |

### 请求示例
```bash
curl -X POST 'http://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/sundy820/modules/default/source_package/link/' \
  -H 'X-BKAPI-AUTHORIZATION: {"access_token": "你的access_token"}' \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryohLfLFHX1EPDP7rB' \
  --data-binary $'------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="package_url"\r\n\r\n   你的源码包链接  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="version"\r\n\r\n  你的版本号  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="allow_overwrite"\r\n\r\nfalse\r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB--\r\n'
```

#### 获取你的 access_token
在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

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

| 字段             | 类型   | 描述       |
| ---------------- | ------ | ---------- |
| version          | string | 版本信息   |
| package_name     | string | 源码包名称 |
| package_size     | string | 源码包大小 |
| sha256_signature | string | sha256数字签名 |
| updated          | string | 更新时间   |
| created          | string | 创建时间   |