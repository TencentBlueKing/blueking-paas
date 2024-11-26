#### Operation Instructions

Open the `app_desc.yaml` file located in the build directory and define the `spec.svcDiscovery.bkSaaS` field for service discovery to obtain the access addresses of other applications on the BlueKing platform. An example file is shown below:

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

The service discovery definition field `spec.svcDiscovery.bkSaaS` is of array structure:
- `bkAppCode`: (required, string) The Code of the BlueKing application.
- `moduleName`: (optional, string) The name of the application's module. If not set, it refers to the "main module" (the module with `isDefault` set to True).

**Note**: If you only need to obtain the main access address of the application and do not care about specific modules, it is recommended not to specify the `moduleName` field.