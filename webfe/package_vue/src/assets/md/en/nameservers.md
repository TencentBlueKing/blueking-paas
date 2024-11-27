This configuration item can be defined in two ways: through an online form or in the application description file `app_desc.yaml` in the code repository. It is recommended to use the application description file for definition.

#### Online Form

For applications deployed via the image repository, you can directly add domain resolution rules on the page, which will take effect after saving and redeploying.

#### Application Description File

For applications deployed from source code, please define `spec.domainResolution.nameservers` in the `app_desc.yaml` file located in the build directory to add additional DNS servers.

Below is an example file:
```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
      # ... omitted
    domainResolution:
      nameservers:
        - "8.8.8.8"
        - "114.114.114.114"
```

Field Descriptions:
- `nameservers`: (array[string]) A list of DNS server addresses, supporting up to 2 entries.

The list of hosts defined here will be merged with the cluster's default DNS server list, ensuring deduplication and joint effectiveness.

> Note: The configuration in the example follows the latest specification of the cloud-native application description file (specVersion: 3). If your description file version is `spec_version: 2`, please convert it to the latest version first.

#### Notes

1. **Scope of Effect**: After definition, all modules under the application will take effect.
2. **Priority**: If this item is defined in the application description file `app_desc.yaml`, it will refresh this configuration item during each deployment.