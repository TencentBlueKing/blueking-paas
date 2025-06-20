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
 * 自定义-快捷选择日期
 */
export const createTimeShortcuts = (i18n, setTimeRangeCache, setTimeShortCutText) => [
  {
    text: i18n.t('最近5分钟'),
    value() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 60 * 1000 * 5);
      return [start, end];
    },
    onClick() {
      setTimeRangeCache && setTimeRangeCache('5m');
      setTimeShortCutText && setTimeShortCutText(i18n.t('最近5分钟'));
    },
  },
  {
    text: i18n.t('最近1小时'),
    value() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 1);
      return [start, end];
    },
    onClick() {
      setTimeRangeCache && setTimeRangeCache('1h');
      setTimeShortCutText && setTimeShortCutText(i18n.t('最近1小时'));
    },
  },
  {
    text: i18n.t('最近3小时'),
    value() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 3);
      return [start, end];
    },
    onClick() {
      setTimeRangeCache && setTimeRangeCache('3h');
      setTimeShortCutText && setTimeShortCutText(i18n.t('最近3小时'));
    },
  },
  {
    text: i18n.t('最近12小时'),
    value() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 12);
      return [start, end];
    },
    onClick() {
      setTimeRangeCache && setTimeRangeCache('12h');
      setTimeShortCutText && setTimeShortCutText(i18n.t('最近12小时'));
    },
  },
  {
    text: i18n.t('最近1天'),
    value() {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24);
      return [start, end];
    },
    onClick() {
      setTimeRangeCache && setTimeRangeCache('1d');
      setTimeShortCutText && setTimeShortCutText(i18n.t('最近1天'));
    },
  },
];

// 长时段快捷选项（天/月级）
export const createLongTermDatePresets = (i18n, setTimeRangeCache, setTimeShortCutText) => {
  const ONE_DAY_MS = 3600 * 1000 * 24;
  const PRESETS = [
    { key: 'today', days: 0, textKey: '今天' },
    { key: '7d', days: 7, textKey: '最近7天' },
    { key: '15d', days: 15, textKey: '最近15天' },
    { key: '30d', days: 30, textKey: '最近30天' },
    { key: '6m', days: 180, textKey: '最近半年' },
  ];

  return PRESETS.map(({ key, days, textKey }) => {
    const text = i18n.t(textKey);
    return {
      text,
      value() {
        const end = new Date();
        const start = new Date();

        if (key === 'today') {
          start.setHours(0, 0, 0, 0);
        } else {
          start.setTime(end.getTime() - ONE_DAY_MS * days);
        }
        return [start, end];
      },
      onClick() {
        setTimeRangeCache?.(key);
        setTimeShortCutText?.(text);
      },
    };
  });
};
