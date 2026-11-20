/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

const ONE_HOUR_MS = 3600 * 1000;
const ONE_DAY_MS = ONE_HOUR_MS * 24;

/**
 * 快捷时间预设
 * - offset: 相对当前时间的毫秒偏移
 * - today: 从当天 00:00:00 开始
 */
const SHORTCUT_PRESETS = [
  { key: '5m', textKey: '最近5分钟', offset: 60 * 1000 * 5 },
  { key: '1h', textKey: '最近1小时', offset: ONE_HOUR_MS },
  { key: '3h', textKey: '最近3小时', offset: ONE_HOUR_MS * 3 },
  { key: '12h', textKey: '最近12小时', offset: ONE_HOUR_MS * 12 },
  { key: '1d', textKey: '最近1天', offset: ONE_DAY_MS },
  { key: 'today', textKey: '今天', today: true },
  { key: '7d', textKey: '最近7天', offset: ONE_DAY_MS * 7 },
  { key: '15d', textKey: '最近15天', offset: ONE_DAY_MS * 15 },
  { key: '30d', textKey: '最近30天', offset: ONE_DAY_MS * 30 },
  { key: '6m', textKey: '最近半年', offset: ONE_DAY_MS * 180 },
];

const PRESET_MAP = new Map(SHORTCUT_PRESETS.map(preset => [preset.key, preset]));

// 分钟级快捷项
export const TIME_SHORTCUT_KEYS = ['5m', '1h', '3h', '12h', '1d'];
// 天/月级快捷项
const LONG_TERM_DATE_KEYS = ['today', '7d', '15d', '30d', '6m'];
// 列表类页面常用组合
export const RECENT_DATE_KEYS = ['today', '7d', '30d', '6m'];

/**
 * 按 key 生成快捷时间项（顺序与传入 keys 一致）
 * @param {Object} i18n 语言实例
 * @param {String[]} keys 预设 key 列表，见 SHORTCUT_PRESETS
 * @param {Function} setTimeRangeCache 点击快捷项时回写时间范围标识
 * @param {Function} setTimeShortCutText 点击快捷项时回写快捷项文案
 */
export const createDateShortcuts = (i18n, keys, setTimeRangeCache, setTimeShortCutText) => keys
  .map(key => PRESET_MAP.get(key))
  .filter(Boolean)
  .map(({ key, textKey, offset, today }) => {
    const text = i18n.t(textKey);
    return {
      text,
      value() {
        const end = new Date();
        const start = new Date();
        if (today) {
          start.setHours(0, 0, 0, 0);
        } else {
          start.setTime(end.getTime() - offset);
        }
        return [start, end];
      },
      onClick() {
        setTimeRangeCache && setTimeRangeCache(key);
        setTimeShortCutText && setTimeShortCutText(text);
      },
    };
  });

/**
 * 获取最近 n 天的时间范围
 * @param {Number} days 天数
 * @returns {[Date, Date]}
 */
export const getRecentDateRange = (days = 7) => {
  const end = new Date();
  const start = new Date();
  start.setTime(end.getTime() - ONE_DAY_MS * days);
  return [start, end];
};

/**
 * 自定义-快捷选择日期（分钟级）
 */
export const createTimeShortcuts = (i18n, setTimeRangeCache, setTimeShortCutText) => createDateShortcuts(
  i18n,
  TIME_SHORTCUT_KEYS,
  setTimeRangeCache,
  setTimeShortCutText,
);

// 长时段快捷选项（天/月级）
export const createLongTermDatePresets = (i18n, setTimeRangeCache, setTimeShortCutText) => createDateShortcuts(
  i18n,
  LONG_TERM_DATE_KEYS,
  setTimeRangeCache,
  setTimeShortCutText,
);
