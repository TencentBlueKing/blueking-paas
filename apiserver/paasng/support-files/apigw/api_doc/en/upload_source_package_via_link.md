### Resource Description
Upload the source code packet to the platform according to the download link

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X POST 'http://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/sundy820/modules/default/source_package/link/' \
  -H 'X-BKAPI-AUTHORIZATION: {"access_token": "Your access_token"}' \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryohLfLFHX1EPDP7rB' \
  --data-binary $'------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="package_url"\r\n\r\n   Link to your source code package  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="version"\r\n\r\n  Your version number  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="allow_overwrite"\r\n\r\nfalse\r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB--\r\n'
```

### Request parameter Description

| Name                                                         | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| package_url *<br/>string($uri)<br/>(formData)<br/>minLength: 1 | Source code package download path<br/>package_url - Source code package download path |
| version<br/>string<br/>(formData)<br/>minLength: 1           | Source package version number<br/>v1                         |
| allow_overwrite<br/>boolean<br/>(formData)<br/>x-nullable: true | Whether to allow overwriting of the original source code package<br/>Default value : false |
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

| version*          | string <br/>title: Version <br/><br/>minlength: 1<br/>version information |
| ----------------- | ------------------------------------------------------------ |
| package_name*     | string <br/>title: Package name <br/>minlength: 1<br/><br/>source package name |
| package_size*     | string <br/>title: Package size <br/>minlength: 1<br/><br/>source package size |
| sha256_signature* | string <br/>title: Sha256 signature <br/>minlength: 1<br/><br/>SHA256 digital signature |
| updated*          | string ($date-time) <br/>title: updated<br/><br/>update time |
| created*          | string ($date-time) <br/>title: created<br/><br/>creation time |