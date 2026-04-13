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
 * @file 首页图表 echarts 配置（兼容 echarts 3.x）
 */

export default function (data, color, options = {}) {
  const allZero = data.every((d) => d.value === 0);
  const { zeroPieColor } = options;

  // 为每项数据设置独立的 label 配置，emphasis 时 value 颜色跟随数据项 color
  const seriesData = data.map((item) => {
    const pieColor = (allZero && zeroPieColor) ? zeroPieColor : (item.itemStyle?.color || item.color);
    return {
      value: item.value,
      name: item.name,
      colorType: item.colorType,
      color: item.color,
      itemStyle: { normal: { color: pieColor } },
      label: {
        normal: {
          show: false,
          position: 'center',
        },
        emphasis: {
          show: true,
          formatter: `{value|${item.value}}\n{name|${item.name}}`,
          textStyle: {
            align: 'center',
            verticalAlign: 'middle',
            rich: {
              value: {
                fontSize: 28,
                fontWeight: 'bold',
                color: item.color || '#313238',
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
        normal: { show: false },
        emphasis: { show: false },
      },
    };
  });

  return {
    tooltip: {
      trigger: 'item',
      formatter(params) {
        return `${params.name}\n${params.value}`;
      },
    },
    legend: {
      orient: 'vertical',
      left: '65%',
      top: 'middle',
      itemHeight: 10,
      itemWidth: 10,
      selectedMode: false,
      data: data.map((item) => {
        const svgCircle = `image://data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10'%3E%3Ccircle cx='5' cy='5' r='5' fill='${encodeURIComponent(item.color)}'/%3E%3C/svg%3E`;
        return {
          name: item.name,
          icon: svgCircle,
          textStyle: {
            color: '#63656E',
            fontSize: 12,
            padding: [3, 0, 0, 0],
          },
        };
      }),
      formatter(name) {
        const item = data.find((d) => d.name === name);
        return `${name}：${item.value}`;
      },
    },
    color: color,
    series: [
      {
        type: 'pie',
        center: ['40%', '50%'],
        radius: ['50', '66'],
        avoidLabelOverlap: false,
        labelLine: {
          normal: { show: false },
          emphasis: { show: false },
        },
        hoverAnimation: !allZero,
        data: seriesData,
      },
    ],
  };
}
