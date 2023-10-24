/* eslint-disable no-param-reassign */
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

import Vue from 'vue';
import App from './App';
import router from '@/router';
import store from '@/store';
import http from '@/api';
import auth from '@/auth';
import { bus } from '@/common/bus';
import $ from 'jquery';
import '@/common/jquery_tools';
// import {
//   bkBadge, bkButton, bkLink, bkCheckbox, bkCheckboxGroup, bkCol, bkCollapse,
// bkCollapseItem, bkContainer, bkDatePicker,
//   bkDialog, bkDropdownMenu, bkException, bkForm, bkFormItem, bkInfoBox, bkInput, bkLoading, bkMessage,
//   bkNavigation, bkNavigationMenu, bkNavigationMenuItem, bkNotify, bkOption, bkOptionGroup, bkPagination,
//   bkPopover, bkProcess, bkProgress, bkRadio, bkRadioGroup,
//   bkRoundProgress, bkRow, bkSearchSelect, bkSelect, bkOverflowTips,
//   bkSideslider, bkSlider, bkSteps, bkSwitcher, bkTab, bkTabPanel, bkTable, bkTableColumn, bkTagInput, bkTimePicker,
//   bkTimeline, bkTransfer, bkTree, bkUpload, bkClickoutside,
//   bkTooltips, bkSwiper, bkRate, bkAnimateNumber, bkVirtualScroll, bkPopconfirm, bkAlert, bkCard,
//   bkTag } from 'bk-magic-vue';

import { bkInfoBox, bkMessage, bkNotify } from 'bk-magic-vue';
import moment from 'moment';
import Clipboard from 'clipboard';
import Directives from '@/directives';
import '@/common/bkmagic.js';
// eslint-disable-next-line
import Blob from '@/common/Blob'
// eslint-disable-next-line
import Export2Excel from '@/common/Export2Excel'
import PaasContentLoader from '@/components/loader';

// 时间格式过滤器引入
import SmartTime from '@/components/filters/SmartTime';
// import 'Extension/tippy.js/dist/tippy.css';
// import 'Extension/tether-drop/dist/css/drop-theme-basic.css';

// // Styles for vex
// import 'Extension/vex-js/sass/vex.sass';
// import 'Extension/vex-js/sass/vex-theme-default.sass';
import passLoading from '@/components/ui/LoadingSlot';

import roundLoading from '@/components/round-loading';
import tableEmpty from '@/components/ui/table-empty';
import emptyDark from '@/components/ui/empty-dark';

import i18n from '@/language/i18n';
// 全量引入自定义图标
import './assets/iconfont/style.css';

// 平台配置
import { PLATFORM_CONFIG } from '../static/json/paas_static.js';

// 表头配置
import { renderHeader } from '@/common/utils';

// markdown样式
import 'github-markdown-css';
// 代码高亮
import 'highlight.js/styles/github.css';

window.$ = $;

Vue.config.devtools = true;

// components use
// Vue.use(bkBadge);
// Vue.use(bkButton);
// Vue.use(bkLink);
// Vue.use(bkCheckbox);
// Vue.use(bkCheckboxGroup);
// Vue.use(bkCol);
// Vue.use(bkCollapse);
// Vue.use(bkCollapseItem);
// Vue.use(bkContainer);
// Vue.use(bkDatePicker);
// Vue.use(bkDialog, {
//   headerPosition: 'left',
// });
// Vue.use(bkDropdownMenu);
// Vue.use(bkException);
// Vue.use(bkForm);
// Vue.use(bkFormItem);
// Vue.use(bkInput);
// Vue.use(bkNavigation);
// Vue.use(bkNavigationMenu);
// Vue.use(bkNavigationMenuItem);
// Vue.use(bkOption);
// Vue.use(bkOptionGroup);
// Vue.use(bkPagination);
// Vue.use(bkPopover);
// Vue.use(bkProcess);
// Vue.use(bkProgress);
// Vue.use(bkRadio);
// Vue.use(bkRadioGroup);
// Vue.use(bkRoundProgress);
// Vue.use(bkRow);
// Vue.use(bkSearchSelect);
// Vue.use(bkSelect);
// Vue.use(bkSideslider);
// Vue.use(bkSlider);
// Vue.use(bkSteps);
// Vue.use(bkSwitcher);
// Vue.use(bkTab);
// Vue.use(bkOverflowTips);
// Vue.use(bkTabPanel);
// Vue.use(bkTable);
// Vue.use(bkTableColumn, {
//   showOverflowTooltip: true,
// });
// Vue.use(bkTagInput, {
//   tooltipKey: 'name',
// });
// Vue.use(bkTimePicker);
// Vue.use(bkTimeline);
// Vue.use(bkTransfer, {
//   showOverflowTips: true,
// });
// Vue.use(bkTree);
// Vue.use(bkUpload);
// Vue.use(bkSwiper);
// Vue.use(bkRate);
// Vue.use(bkAnimateNumber);
// Vue.use(bkVirtualScroll);
// Vue.use(bkPopconfirm);
// // directives use
// Vue.use(bkClickoutside);
// Vue.use(bkTooltips);
// Vue.use(bkLoading);
// // Vue.use(bkOverflowTips)
// Vue.use(bkAlert);
// Vue.use(bkCard);
// Vue.use(bkTag);

Vue.use(Directives);
Vue.component('PaasContentLoader', PaasContentLoader);
Vue.component('PaasLoading', passLoading);
Vue.component('RoundLoading', roundLoading);
Vue.component('TableEmpty', tableEmpty);
Vue.component('EmptyDark', emptyDark);

Vue.prototype.$http = http;
Vue.http = http;

Vue.prototype.$bkInfo = bkInfoBox;
Vue.prototype.$bkMessage = function (config) {
  config.ellipsisLine = 0;
  bkMessage(config);
};
Vue.prototype.$bkNotify = bkNotify;
Vue.prototype.$renderHeader = renderHeader;

Vue.prototype.$paasMessage = function (conf) {
  conf.offsetY = 52;
  conf.limit = 1; // 消息的个数限制
  if (conf.type === 'notify') {
    this.$bkNotify(conf);
  } else {
    conf.ellipsisLine = 0;
    this.$bkMessage(conf);
  }
};

Vue.prototype.catchErrorHandler = function (error) {
  this.$bkMessage({
    theme: 'error',
    message: error.detail || error.message,
  });
};

// 注入全局配置
window.GLOBAL_CONFIG = {
  ...PLATFORM_CONFIG,
  ...window.GLOBAL_CONFIG,
};
Vue.prototype.GLOBAL = window.GLOBAL_CONFIG;

Vue.prototype.smartTime = SmartTime;
window.Clipboard = Clipboard;
window.moment = moment;
window.showDeployTip = function () {
  Vue.prototype.$paasMessage({
    theme: 'error',
    type: 'notify',
    delay: 0,
    title: i18n.t('系统提示'),
    message: i18n.t('静态文件加载失败，请刷新页面重试'),
  });
};

// Request Current User
auth.requestCurrentUser().then((user) => {
  if (!user.isAuthenticated) {
    auth.redirectToLogin();
  } else {
    switch (window.GLOBAL_CONFIG.APP_VERSION) {
      case 'ee':
        document.title = i18n.t('开发者中心 | 腾讯蓝鲸智云');
        break;
      case 'ce':
        document.title = i18n.t('开发者中心 | 腾讯蓝鲸智云');
        break;
      default:
        document.title = i18n.t('开发者中心 | 蓝鲸');
    }

    Vue.config.productionTip = false;

    global.bus = bus;
    global.paasVue = new Vue({
      el: '#app',
      router,
      store,
      i18n,
      components: {
        App,
      },
      created() {
        // 获取功能开头详情
        this.$store.dispatch('getUserFeature');
        this.$store.dispatch('getPlatformFeature');
      },
      methods: {},
      template: '<App />',
    });

    window.GLOBAL_I18N = global.paasVue;
  }
}, (err) => {
  let title = '服务异常';
  let message = '无法连接到后端服务，请稍候再试。';
  let status = 500;
  let link = '';

  if (err.code === 'PRODUCT_NOT_READY') {
    message = err.detail || err.message;
  } else if (err.code === 'NO_ACCESS') {
    status = 403;
    title = '无权限访问';
    message = '你没有相应资源的访问权限，请申请权限或联系管理员授权';
    link = err.apply_url;
  } else if (err.status === 403 && err.code === 1302403) {
    status = 403;
    title = '无该应用访问权限' ;
    message = err.detail || err.message;
  }

  global.paasVue = new Vue({
    el: '#app',
    methods: {},
    template: `<bk-exception class="exception-wrap-item" scene="page" type="${status}" style="position: fixed; top: 40%; transform: translateY(-50%);">
                        <span>${title}</span>
                        <div class="text-subtitle f12 mt20 mb20" style="color: #979BA5;">${message}</div>
                        <div class="text-wrap" v-if="${status === 403 && !!link}">
                            <a class="text-btn bk-primary bk-button-normal bk-button" href="${link}">去申请</a>
                        </div>
                    </bk-exception>`,
  });
});
