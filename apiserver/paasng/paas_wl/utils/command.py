import os


def get_command_name(command: str) -> str:
    """Get name from command"""
    # fit for old paas app celery start by django-celery: python manage.py celery beat/worker....
    if command.startswith("python manage.py celery"):
        return "celery"

    process_exec = command.split(' ')[0]
    return os.path.basename(process_exec)
