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

const option = {
  'color': ['#3a84ff'],
  'yAxis': [
    {
      'name': '',
      'minInterval': 1,
      'nameTextStyle': {
        'color': 'red'
      },
      'boundaryGap': [0, '20%'],
      'type': 'value',
      'axisLine': {
        'show': true,
        'lineStyle': {
          'color': '#dde4eb'
        }
      },
      'axisTick': {
        'alignWithLabel': true,
        'length': 0,
        'lineStyle': {
          'color': 'red'
        }
      },
      'axisLabel': {
        'color': '#868b97'
      },
      'splitLine': {
        'show': true,
        'lineStyle': {
          'color': ['#ebf0f5'],
          'type': 'dashed'
        }
      }
    }
  ],
  'title': {
    'text': '',
    'x': 'center',
    'textStyle': {
      'color': '#63656e',
      'fontSize': 13,
      'align': 'center'
    }
  },
  'series': [],
  'tooltip': {
    'axisPointer': {
      'type': 'shadow'
    },
    'trigger': 'item',
    'formatter': function (data) {
      return '';
    }
  },
  'grid': {
    'show': false,
    'top': '15%',
    'left': '3%',
    'right': '3%',
    'bottom': '11%',
    'containLabel': true
  },
  'xAxis': {
    'data': [],
    'type': 'category',
    'axisLine': {
      'show': true,
      'lineStyle': {
        'color': '#dde4eb'
      }
    },
    'axisLabel': {
      'show': true,
      'color': '#878c97'
    },
    'axisTick': {
      'alignWithLabel': true,
      'length': 5,
      'lineStyle': {
        'color': '#ebf0f5'
      }
    },
    'splitLine': {
      'show': true,
      'lineStyle': {
        'color': ['#ebf0f5'],
        'type': 'dashed'
      }
    }
  }
};

export default option;
