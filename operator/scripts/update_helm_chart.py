# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import argparse
import difflib
import shutil
from os import path, walk
from pathlib import Path
from textwrap import dedent, indent

import yaml

TMPL_DIR = 'templates'


def wrap_multiline_str(space_num: int, m_string: str) -> str:
    """对多行字符串做处理，避免格式化时候丢失缩进"""
    return indent(dedent(m_string), ' ' * space_num)


# 新 chart 中的模板文件是平铺的，但是到实际的 chart 中是分目录的，
# 这里即文件的目标目录 & 文件的映射关系，后续可按照需求添加
filepath_conf = {
    '_helpers.tpl': '_helpers.tpl',
    # crd
    'bkapp-crd.yaml': 'crds/paas.bk.tencent.com_bkapps.yaml',
    'domaingroupmapping-crd.yaml': 'crds/paas.bk.tencent.com_domaingroupmappings.yaml',
    'projectconfig-crd.yaml': 'crds/paas.bk.tencent.com_projectconfigs.yaml',
    # controller
    'deployment.yaml': 'controller/deployment.yaml',
    'manager-config.yaml': 'controller/config.yaml',
    'metrics-service.yaml': 'controller/service.yaml',
    'leader-election-rbac.yaml': 'controller/leader-election-rbac.yaml',
    'manager-rbac.yaml': 'controller/manager-rbac.yaml',
    'metrics-reader-rbac.yaml': 'controller/metrics-reader-rbac.yaml',
    'proxy-rbac.yaml': 'controller/proxy-rbac.yaml',
    # webhooks
    'selfsigned-issuer.yaml': 'webhooks/selfsigned-issuer.yaml',
    'serving-cert.yaml': 'webhooks/serving-cert.yaml',
    'mutating-webhook-configuration.yaml': 'webhooks/mutating-webhook-configuration.yaml',
    'validating-webhook-configuration.yaml': 'webhooks/validating-webhook-configuration.yaml',
    'webhook-service.yaml': 'webhooks/webhook-service.yaml',
}

# 格式：文件路径: [(src_str1, dst_str1), (src_str2, dst_str2)]
content_patch_conf = {
    'deployment.yaml': [
        # 替换 rbac-proxy 镜像
        (
            wrap_multiline_str(
                8,
                """
        image: {{ .Values.controllerManager.kubeRbacProxy.image.repository }}:{{ .Values.controllerManager.kubeRbacProxy.image.tag | default .Chart.AppVersion }}
            """,
            ),
            wrap_multiline_str(
                8,
                """
        image: {{ include "bkpaas-app-operator.proxyImage" . }}
        imagePullPolicy: {{ .Values.image.pullPolicy }}
            """,
            ),
        ),
        # 替换 operator 镜像
        (
            wrap_multiline_str(
                8,
                """
        image: {{ .Values.controllerManager.manager.image.repository }}:{{ .Values.controllerManager.manager.image.tag | default .Chart.AppVersion }}
            """,
            ),
            wrap_multiline_str(
                8,
                """
        image: {{ include "bkpaas-app-operator.image" . }}
        imagePullPolicy: {{ .Values.image.pullPolicy }}
            """,
            ),
        ),
        # 替换 rbac-proxy resources 为固定值
        (
            wrap_multiline_str(
                8,
                """
        resources: {{- toYaml .Values.controllerManager.kubeRbacProxy.resources | nindent 10 }}
            """,
            ),
            wrap_multiline_str(
                8,
                """
        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 5m
            memory: 64Mi
            """,
            ),
        ),
        # 替换 operator 资源配额
        (
            '.Values.controllerManager.manager.resources',
            '.Values.resources',
        ),
        # 替换 imagePullSecrets，改成引用 values
        (
            wrap_multiline_str(
                6,
                """
      imagePullSecrets:
      - name: {{ include "bkpaas-app-operator.fullname" . }}-docker-registry
            """,
            ),
            wrap_multiline_str(
                6,
                """
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
            """,
            ),
        ),
        # 替换副本数量引用
        (
            '.Values.controllerManager.replicas',
            '.Values.replicaCount',
        ),
    ],
    'manager-config.yaml': [
        ('.Values.managerConfig.controllerManagerConfigYaml', '.Values.controllerConfig'),
        (
            # 白名单控制支持 enabled & 挪到 values 顶层
            wrap_multiline_str(
                6,
                """
      accessControlConfig:
        redisConfigKey: {{ .Values.controllerConfig.ingressPluginConfig.accessControlConfig.redisConfigKey | quote }}
            """,
            ),
            wrap_multiline_str(
                6,
                """
      {{ if .Values.accessControl.enabled -}}
      accessControlConfig:
        redisConfigKey: {{ .Values.accessControl.redisConfigKey }}
      {{- end -}}
            """,
            ),
        ),
        (
            # 平台配置挪到 values 顶层
            '.Values.controllerConfig.platformConfig',
            '.Values.platformConfig',
        ),
    ],
}

content_append_conf = {
    '_helpers.tpl': """
{{/*
Image Tag
*/}}
{{- define "bkpaas-app-operator.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.image "global" .Values.global) }}
{{- end -}}

{{/*
Proxy Image Tag
*/}}
{{- define "bkpaas-app-operator.proxyImage" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.proxyImage "global" .Values.global) }}
{{- end -}}
"""
}


class HelmChartUpdator:
    def __init__(self, chart_target_dir: str):
        self.chart_target_dir = Path(chart_target_dir)
        self.chart_source_dir = Path(__file__).resolve().parents[1] / 'bkpaas-app-operator'

    def update(self):
        # 1. 检查目标 chart 是否合法
        self._check_target_chart()

        self._print_dividing_line()

        # 2.1 移除不需要的换行
        self._remove_useless_newline()
        # 2.2 patch 部分 chart 文件内容
        self._patch_chart_file_contents()
        # 2.3 部分 chart 文件追加内容
        self._append_chart_file_contents()
        # 2.4 使用处理完的 chart 文件替换原 chart 的
        self._replace_chart_yaml_files()
        # 2.5 检查是否存在未处理的文件
        self._check_left_files()

        self._print_dividing_line()

        # 3.1 patch values 文件
        self._patch_values_file()
        # 3.2 对新旧 values 文件进行 diff，输出需要手动修改的
        self._diff_values()

        self._print_dividing_line()

        # 4. 清理工作空间
        self._clear_workspace()

    def _check_target_chart(self):
        """检查目标路径的 chart 是否存在"""
        if not path.isfile(self.chart_target_dir / 'Chart.yaml'):
            raise Exception('target chart.yaml not exists')

        if not path.isfile(self.chart_target_dir / 'values.yaml'):
            raise Exception('target values.yaml not exists')

        if not path.isdir(self.chart_target_dir / TMPL_DIR):
            raise Exception(f'target {TMPL_DIR} dir not exists')

        for sub_tmpl_dir in ['crds', 'controller', 'webhooks']:
            if not path.isdir(self.chart_target_dir / TMPL_DIR / sub_tmpl_dir):
                raise Exception(f'target {TMPL_DIR}/{sub_tmpl_dir} dir not exists')

    def _patch_chart_file_contents(self):
        """对 chart 文件的部分内容进行替换"""
        for filepath, patch_list in content_patch_conf.items():
            fp = self.chart_source_dir / TMPL_DIR / filepath

            contents = fp.read_text()
            for src_str, dst_str in patch_list:
                contents = contents.replace(src_str, dst_str)

            fp.write_text(contents)

    def _append_chart_file_contents(self):
        """对部分文件追加内容"""
        for filepath, contents in content_append_conf.items():
            with open(path.join(self.chart_source_dir, TMPL_DIR, filepath), 'a') as fw:
                fw.write(contents)

    def _remove_useless_newline(self):
        """去除 go-yaml unmarshal 中不需要的换行"""
        for filepath in filepath_conf:
            if not filepath.endswith('yaml'):
                continue

            fp = self.chart_source_dir / TMPL_DIR / filepath
            contents = fp.read_text().splitlines()

            for idx in range(len(contents)):
                # 忽略第一行，因为首行不会是被强制换行的
                if (
                    idx
                    and contents[idx].count('}}')
                    and contents[idx - 1].count('{{') - contents[idx - 1].count('}}') == 1
                ):
                    # 去掉上一行原来的换行符，拼接上当前行，把当前行设置为空字符串
                    contents[idx - 1] = contents[idx - 1].rstrip() + ' '
                    contents[idx - 1] += contents[idx].lstrip()
                    contents[idx] = ''

            fp.write_text('\n'.join([line for line in contents if line]))

    def _replace_chart_yaml_files(self):
        """使用新的 Charts 中的文件，替换原有的文件"""
        for src, dst in filepath_conf.items():
            print(f'replace [{dst}] with [{src}]...')
            shutil.move(self.chart_source_dir / TMPL_DIR / src, self.chart_target_dir / TMPL_DIR / dst)

        print(f'successfully replace {len(filepath_conf)} chart files!')

    def _check_left_files(self):
        # 有些文件是开发用的，不需要放到 chart 中，在检查时候跳过
        not_chart_required_files = ['docker-registry.yaml']

        dir = self.chart_source_dir / TMPL_DIR
        for root, _, files in walk(dir):
            for file in files:
                if file in not_chart_required_files:
                    continue
                raise Exception(f"Some files are left in the directory ({dir}), please check if they are needed")

    def _patch_values_file(self):
        """对 values 中的部分配置进行调整"""
        fp = self.chart_source_dir / 'values.yaml'
        values = yaml.load(fp.read_text(), yaml.SafeLoader)

        # 镜像，副本等平铺
        values['proxyImage'] = {
            'registry': 'hub.bktencent.com',
            'repository': 'blueking/kube-rbac-proxy',
            'pullPolicy': 'IfNotPresent',
            'tag': 'v0.12.0',
        }
        values['image'] = {
            'registry': 'hub.bktencent.com',
            'repository': 'blueking/bkpaas-app-operator',
            'pullPolicy': 'IfNotPresent',
            'tag': '0.0.1',
        }
        values['replicaCount'] = values['controllerManager']['replicas']
        values['resources'] = values['controllerManager']['manager']['resources']

        del values['controllerManager']

        # 镜像拉取凭证
        del values['dockerRegistry']
        values['imagePullSecrets'] = []

        # 名称相关
        values['nameOverride'] = ''
        values['fullnameOverride'] = ''

        # manager 配置相关
        values['controllerConfig'] = values['managerConfig']['controllerManagerConfigYaml']
        del values['managerConfig']

        # 白名单控制配置挪到顶层
        values['accessControl'] = {'enabled': False, 'redisConfigKey': ''}
        del values['controllerConfig']['ingressPluginConfig']

        # 平台配置挪到顶层
        values['platformConfig'] = values['controllerConfig']['platformConfig']
        del values['controllerConfig']['platformConfig']

        fp.write_text(yaml.dump(values))

    def _diff_values(self):
        """
        生成新旧 values 的 diff 结果，人工处理！
        不直接替换的原因是无法保留原有 values 中的注释，空行，顺序等
        """
        new_fp = self.chart_source_dir / 'values.yaml'
        new_values = new_fp.read_text().splitlines()

        old_fp = self.chart_target_dir / 'values.yaml'
        old_values = yaml.dump(yaml.load(old_fp.read_text(), yaml.SafeLoader)).splitlines()

        diff_rets = list(difflib.unified_diff(old_values, new_values, 'old', 'new'))
        if not diff_rets:
            print('diff values file found nothing...')
            return

        print('diff values file found something need to be resolved...')
        for line in difflib.unified_diff(old_values, new_values, 'old', 'new'):
            print(line)

    def _clear_workspace(self):
        """一切执行完成后，清理工作空间"""
        print('clear workspace...')
        shutil.rmtree(self.chart_source_dir)

    @staticmethod
    def _print_dividing_line():
        print('\n============================================================\n')


if __name__ == "__main__":
    """根据 helmify 生成的新 Chart，更新原来的 Chart"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', type=str, default='/tmp/bkpaas-app-operator')
    args = parser.parse_args()

    HelmChartUpdator(args.d).update()
