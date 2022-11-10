# -*- coding: utf-8 -*-

from django.db import models

from paas_wl.platform.applications.models import UuidAuditedModel


class OutputStream(UuidAuditedModel):
    def write(self, line, stream='STDOUT'):
        if not line.endswith('\n'):
            line += '\n'
        OutputStreamLine.objects.create(output_stream=self, line=line, stream=stream)


class OutputStreamLine(models.Model):
    output_stream = models.ForeignKey('OutputStream', related_name='lines', on_delete=models.CASCADE)
    stream = models.CharField(max_length=16)
    line = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created']

    def __str__(self):
        return '%s-%s' % (self.id, self.line)


class OneOffCommand(UuidAuditedModel):
    """这个类是没用的不要再看了"""

    operator = models.CharField(max_length=64, null=True)
    command = models.TextField()
    # release = models.ForeignKey('Release', null=True, on_delete=models.SET_NULL)
    output_stream = models.OneToOneField('OutputStream', null=True, on_delete=models.CASCADE)
    exit_code = models.SmallIntegerField('ExitCode', null=True)
    build = models.ForeignKey('Build', null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['created']
        get_latest_by = 'created'

    def __str__(self):
        return self.command

    def write_output(self, line):
        self.output_stream.write(line=line)

    def write_error_info(self, exit_code):
        self.output_stream.write("one-off command exit with: %s" % exit_code)

        self.exit_code = int(exit_code)
        self.save()

    def success_exit(self):
        self.exit_code = 0
        self.save()
