An app module can run multiple processes, such as web and worker. You can configure these processes via the `app_desc.yaml` file in your source repository.

#### 1. How-to

Open the `app_desc.yaml` file in the project's root directory (create it if it doesn't exist), and edit the `module.processes` field to set up processes.

Below is an example file defining two processes: `web` and `worker`:

```yaml
spec_version: 2
module:
  language: Python
  processes:
    web:
      command: gunicorn wsgi -w 4 -b [::]:${PORT}
    worker:
      command: celery -A app -l info
```

The `processes` field's keys are the process names, and the values contain process details. The `command` is the start command for the process, supporting the use of `${VAR_NAME}` to reference environment variables.

After modifying the `app_desc.yaml`, push the changes to the repository and **redeploy the module** to activate the new process configuration.

#### Notes

1. Process name requirements: Start with a lowercase letter or number, include lowercase letters, numbers, and hyphens (`-`), and be no more than 12 characters long.
2. If the module has a special "build directory," the `app_desc.yaml` file should be placed there, not in the repository's root directory.

> Further reading: [Introduction to Application Processes](PROCFILE_DOC) | [Application Description File](APP_DESC_DOC)