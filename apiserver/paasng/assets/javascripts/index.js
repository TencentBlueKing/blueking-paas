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
