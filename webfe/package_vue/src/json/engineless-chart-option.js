/*
* Tencent is pleased to support the open source community by making
* 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
* Copyright (C) 2017-2022THL A29 Limited, a Tencent company.  All rights reserved.
* Licensed under the MIT License (the "License").
* You may not use this file except in compliance with the License.
* You may obtain a copy of the License at http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*
* We undertake not to change the open source license (MIT license) applicable
*
* to the current version of the project delivered to anyone in the future.
*/

/**
 * @file echarts 图表配置
 */
import i18n from '@/language/i18n';
export default {
  config: {
    title: {
      text: i18n.t('网关名'),
      top: 'bottom',
      left: 'center',
      textStyle: {
        color: '#979BA5',
        fontWeight: 'normal',
        fontSize: 12
      }
    },
    grid: {
      left: '5%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    legend: {
      show: true,
      top: 20,
      icon: 'rect',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: {
        fontSize: 12,
        lineHeight: 14,
        rich: {
          a: {
            verticalAlign: 'middle'
          }
        },
        padding: [0, 0, -2, 0]
      },
      data: [i18n.t('API 数量')]
    },
    xAxis: {
      type: 'category',
      data: [],
      // 设置横轴
      axisLine: {
        show: true,
        lineStyle: {
          color: '#DCDEE5'
        }
      },
      // 设置横轴坐标刻度
      axisTick: {
        show: false
      },
      // 设置横轴文字
      axisLabel: {
        color: '#979BA5',
        formatter (value, index) {
          let ret = value;
          if (value) {
            ret = value.replace(' ', '\n');
          }
          return ret;
        }
      }
    },
    yAxis: {
      type: 'value',
      // 设置纵轴线条
      axisLine: {
        show: true,
        lineStyle: {
          color: '#DCDEE5'
        }
      },
      // 设置纵轴刻度
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#979BA5'
      },
      // 设置网格s
      splitLine: {
        show: true,
        // 设置纵轴文字
        axisLabel: {
          color: '#8a8f99',
          formatter (value, index) {
            return `${value}`;
          }
        },
        lineStyle: {
          color: ['#ecf0f4'],
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: i18n.t('API 数量'),
        data: [],
        type: 'bar',
        barMaxWidth: 24,
        itemStyle: {
          normal: {
            color: '#3A84FF'
          }
        }
      }
    ]
  }
};
