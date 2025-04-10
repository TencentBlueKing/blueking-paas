An app module can run multiple processes, such as web and worker. You can configure these processes via the `app_desc.yaml` file in your source repository.

#### 1. How-to

Open the `app_desc.yaml` file in the project's root directory (create it if it doesn't exist), and edit the `module.processes` field to set up processes.

Below is an example file defining two processes: `web` and `worker`:

```yaml
specVersion: 3
module:
  name: default
  language: Python
  spec:
    processes:
      - name: web
        procCommand: gunicorn wsgi -w 4 -b [::]:${PORT}
        services:
          - name: web
            protocol: TCP
            exposedType:
              name: bk/http
            targetPort: 5000
            port: 80
      - name: worker
        procCommand: celery -A app -l info
        services:
          - name: worker
            protocol: TCP
            targetPort: 5000
            port: 80
```

The `processes` field contains a list of processes, with each process specified by a `name` field. The procCommand is the startup command for the process, and it supports using `${VAR_NAME}` to reference environment variables.

After modifying the `app_desc.yaml`, push the changes to the repository and **redeploy the module** to activate the new process configuration.

#### Notes

1. Process name requirements: Start with a lowercase letter or number, include lowercase letters, numbers, and hyphens (`-`), and be no more than 12 characters long.
2. If the module has a special "build directory," the `app_desc.yaml` file should be placed there, not in the repository's root directory.

> Further reading: [Introduction to Application Processes](PROCFILE_DOC) | [Application Description File](APP_DESC_CNATIVE)
