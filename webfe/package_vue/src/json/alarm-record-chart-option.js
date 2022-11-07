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
export default {
    title: {
        show: false
    },
    tooltip: {
        trigger: 'axis',
        axisPointer: {
            type: 'line',
            animation: true,
            label: {
                backgroundColor: '#6a7985'
            }
        },
        formatter (params, ticket, callback) {
            let ret = `<div>${params[0].axisValueLabel}</div>`;
            params.forEach(item => {
                let val = parseFloat(item.value).toFixed(2);
                if (val === '0.00') {
                    val = 0;
                }
                ret += `<div>${item.seriesName}：${val}</div>`;
            });
            return ret;
        }
    },
    toolbox: {
        show: false
    },
    grid: {
        top: '3%',
        left: '0%',
        right: '4%',
        bottom: '5%',
        containLabel: true
    },
    xAxis: {
        type: 'category',
        // 设置横轴坐标刻度
        axisTick: {
            show: false
        },
        axisLine: {
            show: true,
            lineStyle: {
                color: '#dde3ea'
            }
        },
        // 设置横轴文字
        axisLabel: {
            color: '#8a8f99',
            formatter (value, index) {
                let ret = value;
                if (value) {
                    ret = value.replace(' ', '\n');
                }
                return ret;
            }
        },
        data: []
    },
    yAxis: {
        boundaryGap: [0, '2%'],
        type: 'value',
        // 设置纵轴线条
        axisLine: {
            show: true,
            lineStyle: {
                color: '#dde3ea'
            }
        },
        // 设置纵轴刻度
        axisTick: {
            show: false
        },
        // 设置纵轴文字
        axisLabel: {
            color: '#8a8f99',
            formatter (value, index) {
                return `${value}`;
            }
        }
    },
    series: []
};
