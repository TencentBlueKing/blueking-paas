#### Operation Instructions

Open the `app_desc.yaml` file located in the build directory and define `spec.domainResolution.nameservers` to add additional DNS servers. An example file is shown below:

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

**Note**: The list of hosts defined here will be merged with the default DNS server list of the cluster, ensuring deduplication and joint effectiveness.