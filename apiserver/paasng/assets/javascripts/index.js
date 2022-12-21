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
import Vue from 'vue'
import 'Extension/bootstrap-loader'
import 'BkMagicVue/dist/bk-magic-vue.min.css'
import 'Extension/vue-json-pretty/lib/styles.css'
import ToggleButton from 'Extension/vue-js-toggle-button/src/Button'
import VueJsonPretty from 'Extension/vue-json-pretty'
import moment from 'Extension/moment'
import http from 'Lib/api'
import bkMagic from 'BkMagicVue'
import Pagination from 'Lib/components/Pagination'
import JsonEditorComponent from 'Lib/components/JsonEditor'
import SimpleMDEComponent from 'Lib/components/SimpleMDE'
import UserSelector from 'Lib/components/UserSelector'
import draggable from 'vuedraggable'
const querystring = require('querystring');
import 'Styles/admin/base.scss'

window.Vue = Vue
Vue.use(bkMagic)
Vue.component("pagination", Pagination)
Vue.component("toggle-button", ToggleButton)
Vue.component("json-pretty", VueJsonPretty)
Vue.component('json-editor', JsonEditorComponent)
Vue.component('vue-simple-mde', SimpleMDEComponent)
Vue.component('user-selector', UserSelector)
Vue.component('draggable', draggable)

window.querystring = querystring
window.Vue.prototype.$paasMessage = function (conf) {
    conf.offsetY = 80
    conf.limit = 1 // 消息的个数限制
    if (conf.type === 'notify') {
        this.$bkNotify(conf)
    } else {
        conf.ellipsisLine = 0
        this.$bkMessage(conf)
    }
}


window.moment = moment
window.moment.locale('zh-cn')
