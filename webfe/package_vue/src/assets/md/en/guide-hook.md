Define "hooks" to trigger specific commands at certain points during deployment, suitable for tasks like environment setup and database changes.

#### 1. Configure the "pre_release" hook

The "pre_release" hook executes **after build completion and before deployment process**. It's ideal for tasks like database schema changes.

To create a pre-release hook, modify the `module.scripts` field in the `app_desc.yaml` file. Here's an example:

```yaml
spec_version: 2
module:
  language: Python
  scripts:
    pre_release_hook: "python manage.py migrate --no-input"
  processes:
	# ...omitted
```

#### Notes

1. A fresh container is used when executing the "pre_release" hook and not the one from the build phase. Therefore, changes to local files during the build **won't affect** the hook's execution environment.

> Further reading: [Deployment Stage Hooks](DEPLOY_ORDER) | [Build Stage Hooks](BUILD_PHASE_HOOK)