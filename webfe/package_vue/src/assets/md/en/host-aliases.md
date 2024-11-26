#### Operation Instructions

Open the `app_desc.yaml` file located in the build directory and define `spec.domainResolution.hostAliases` to add additional domain resolution rules (equivalent to appending entries to the /etc/hosts file). An example file is shown below:

```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
      # ... omitted
    domainResolution:
      hostAliases:
        - ip: "127.0.0.1"
          hostnames:
            - "foo.local"
            - "bar.local"
```

Field Descriptions:
- `ip`: (string) The target IP address to resolve.
- `hostnames`: (array[string]) The list of domain names to be resolved.

**Note**: In the example configuration, when the application accesses the domains `foo.local` and `bar.local`, they will be resolved to the target IP address `127.0.0.1`.