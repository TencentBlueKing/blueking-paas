This configuration item can be defined in two ways: through an online form or the application description file. It is recommended to use the application description file for definition.

#### Online Form

For applications deployed via the image repository, you can directly add service discovery on the page, which will take effect after saving and redeploying.

#### Application Description File

For applications deployed from source code, please define the `spec.svcDiscovery.bkSaaS` field in the `app_desc.yaml` file located in the build directory to implement service discovery and obtain the access addresses of other applications on the BlueKing platform.

Below is an example file:
```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
    # ... omitted
    svcDiscovery:
      bkSaaS:
        - bkAppCode: bk-iam
        - bkAppCode: bk-user
          moduleName: api
```

The service discovery definition field spec.svcDiscovery.bkSaaS is of array structure:
- `bkAppCode`: (required, string) The Code of the BlueKing application.
- `moduleName`: (optional, string) The name of the application's module. If not set, it refers to the "main module" (the module with `isDefault` set to True).

If you only need to obtain the main access address of the application and do not care about specific modules, it is recommended not to specify the `moduleName` field.

> Note: The configuration in the example follows the latest specification of the cloud-native application description file (specVersion: 3). If your description file version is `spec_version: 2`, please convert it to the latest version first.

#### Notes

1. **Scope of Effect**: After definition, all modules under the application will take effect.
2. **Priority**: If this item is defined in the application description file `app_desc.yaml`, it will refresh this configuration item during each deployment.