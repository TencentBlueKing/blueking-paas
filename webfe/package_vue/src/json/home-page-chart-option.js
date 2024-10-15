/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

/**
 * @file 首页告警情况 echarts 图表配置
 */

export default function (data, color) {
  // 判断是否为空
  const allZero = data.every(d => d.value === 0);
  const legendIcons = [
    'image:///static/images/circle-home1.svg',
    'image:///static/images/circle-home2.svg',
  ];
  return {
    tooltip: {
      trigger: 'item',
      formatter(params) {
        return `${params.name}\n${params.value}`;
      },
    },
    legend: {
      orient: 'vertical',
      left: '60%',
      top: 'middle',
      itemHeight: 10,
      itemWidth: 10,
      selectedMode: false,
      data: data.map((item, index) => ({
        name: item.name,
        icon: allZero ? legendIcons[index] : 'circle',
        textStyle: {
          color: '#63656E',
          fontSize: 12,
          padding: [3, 0, 0, 0],
        },
      })),
      formatter(name) {
        const item = data.find(d => d.name === name);
        return `${name}：${item.value}`;
      },
    },
    color: allZero ? ['#B5E0AB'] : color,
    series: [
      {
        type: 'pie',
        center: ['40%', '50%'],
        radius: ['50', '66'],
        avoidLabelOverlap: false,
        label: {
          normal: {
            show: false,
            position: 'center',
            formatter: '',
          },
          emphasis: {
            show: true,
            formatter: params => `{value|${params.value}}\n{name|${params.name}}`,
            textStyle: {
              align: 'center',
              verticalAlign: 'middle',
              rich: {
                value: {
                  fontSize: 28,
                  fontWeight: 'bold',
                  color: '#EA3636',
                  align: 'center',
                  lineHeight: 40,
                },
                name: {
                  fontSize: 12,
                  color: '#63656E',
                  align: 'center',
                },
              },
            },
          },
        },
        labelLine: {
          normal: {
            show: false,
          },
        },
        // 当数据为0时，不进行动画（不缩放）
        hoverAnimation: !allZero,
        data,
      },
    ],
  };
}
