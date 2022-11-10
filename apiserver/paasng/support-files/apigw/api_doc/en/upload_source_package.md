### Resource Description
Upload source code package to platform

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Request parameter Description

| Name                                                         | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| package  * <br/>file <br/>(formdata)                         | source package file                                          |
| Allow_overwrite <br/>boolean <br/>(formdata) <br/>x exclusive nullable: true | whether to allow overwriting of original source code packets |
| code *<br/>string<br/>(path)                                 | code                                                         |
| module_name *<br/>string<br/>(path)                          | module_name                                                  |


### Return result
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

### Return result description

| version*          | string<br/>title: Version<br/>minLength: 1<br/><br/>版本信息 |
| ----------------- | ------------------------------------------------------------ |
| package_name*     | string<br/>title: Package name<br/>minLength: 1<br/><br/>源码包名称 |
| package_size      | string<br/>title: Package size<br/>minLength: 1<br/><br/>源码包大小 |
| sha256_signature* | string<br/>title: Sha256 signature<br/>minLength: 1<br/><br/>sha256数字签名 |
| updated*          | string($date-time)<br/>title: Updated<br/><br/>更新时间      |
| created*          | string($date-time)<br/>title: Created<br/><br/>创建时间      |