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

import _ from 'lodash';
import moment from 'moment';

class CustomRanges {
    /*
     * Custom Rranger object for generating custom range buttons for
     * bootstrap-daterangepicker options.
     */
    constructor (values) {
        this.SPEC_DATE = moment();
        this.values = values;

        // Init valuesMap
        this.valuesMap = {};
        _.forEach(this.values, (item) => {
            this.valuesMap[item.label] = item.value;
        });

        // Init rangesMap
        this.rangesMap = {};
        _.forEach(this.values, (item, index) => {
            const dtEnd = this.SPEC_DATE.clone();
            let dtStart;
            if (/^\d+(y|Q|M|w|d|h|m|s|ms)$/.test(item.value)) {
                // item.value = '12h'
                //  => .subtract(12, 'h')
                dtStart = dtEnd.clone().subtract(
                    parseInt(item.value.substring(0, item.value.length - 1)),
                    item.value[item.value.length - 1]
                );
            } else {
                dtStart = dtEnd.clone().subtract(index + 1, 's');
            }

            this.rangesMap[item.label] = [dtStart, dtEnd];
        });
    }
    hasLabel (label) {
        return _.has(this.valuesMap, label);
    }
    getValue (label) {
        return this.valuesMap[label];
    }
    getRanges (label) {
        return this.rangesMap[label];
    }
    getRangesParam () {
        return this.rangesMap;
    }
}

const OPTIONS_DEFAULT = {
    linkedCalendars: false,
    autoUpdateInput: false,
    showDropdowns: true,
    timePicker: true,
    timePicker24Hour: true,
    timePickerIncrement: 1,
    timePickerSeconds: false,
    opens: 'right'
};

const OPTIONS_LOCALE_ZH = {
    format: 'YYYY-MM-DD HH:mm:ss',
    separator: ' 至 ',
    applyLabel: '确定',
    cancelLabel: '取消',
    fromLabel: '从',
    toLabel: '到',
    weekLabel: '周',
    customRangeLabel: '自定义',
    daysOfWeek: [
        '日',
        '一',
        '二',
        '三',
        '四',
        '五',
        '六'
    ],
    monthNames: [
        '一月',
        '二月',
        '三月',
        '四月',
        '五月',
        '六月',
        '七月',
        '八月',
        '九月',
        '十月',
        '十一月',
        '十二月'
    ],
    firstDay: 1
};

export {
    CustomRanges,
    OPTIONS_DEFAULT,
    OPTIONS_LOCALE_ZH
};
