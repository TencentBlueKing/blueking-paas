<template>
    <div :class="[memberClass, extCls]" @click.capture="handleClick">
        <bk-tag-input
            v-model="tags"
            ref="tagInput"
            :placeholder="defaultPlaceholder"
            :disabled="disabled || isLoading"
            :save-key="saveKey"
            :display-key="displayKey"
            :search-key="searchKey"
            :has-delete-icon="hasDeleteIcon"
            :max-data="maxData"
            :max-result="maxResult"
            :content-width="contentWidth"
            :list="renderList"
            :tag-tpl="tagTpl"
            :tpl="tpl"
            :filter-callback="filterCallback"
            :tooltip-key="tooltipKey"
            @change="change"
            @select="select"
            @remove="remove">
        </bk-tag-input>
        <img class="bk-member-loading" v-if="isLoading" src="./spinner.svg">
    </div>
</template>

<script>
    import locale from 'bk-magic-vue/lib/locale';
    import emitter from './emitter.js';
    import getLoginUrl from './constants';

    // 获取唯一随机数
    export function uuid () {
        let id = '';
        const randomNum = Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1);

        for (let i = 0; i < 7; i++) {
            id += randomNum;
        }
        return id;
    }

    export default {
        name: 'bk-member-selector',
        mixins: [locale.mixin, emitter],
        props: {
            placeholder: {
                type: String,
                default: ''
            },
            disabled: {
                type: Boolean,
                default: false
            },
            hasDeleteIcon: {
                type: Boolean,
                default: false
            },
            contentWidth: {
                type: Number,
                default: 190
            },
            type: {
                type: String,
                default: 'rtx'
            },
            value: {
                type: Array,
                default () {
                    return [];
                }
            },
            maxData: {
                type: Number,
                default: -1
            },
            maxResult: {
                type: Number,
                default: 10
            },
            // 外部设置的 class name
            extCls: {
                type: String,
                default: ''
            },
            tooltipKey: {
                type: String,
                default: ''
            }
        },
        data () {
            return {
                saveKey: this.type === 'email' ? 'Name' : 'english_name',
                displayKey: this.type === 'email' ? 'Name' : this.type === 'all' ? 'english_name' : 'english_name',
                searchKey: this.type === 'email' ? 'FullName' : 'english_name',
                renderList: [],
                tags: [],
                defaultPlaceholder: '',
                isLoading: true,
                needsLogin: false
            };
        },
        computed: {
            memberClass () {
                return `bk-${this.type}-member-selector`;
            },
            selectedList () {
                return this.$refs.tagInput.localTagList.slice(0);
            }
        },
        watch: {
            value (newVal, oldVal) {
                if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
                    this.tags = [...this.value];
                }
            },
            tags (newVal, oldVal) {
                if (JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
                    this.$emit('input', [...newVal]);
                }
            }
        },
        created () {
            this.defaultPlaceholder = this.placeholder || this.$t('请输入并按Enter结束');
            window.addEventListener('message', this.messageListener, false);
        },
        mounted () {
            this.requestList();
            this.tags = [...this.value];
            this.$nextTick(() => {
                this.$refs.tagInput.localTagList = this.tags.map(tag => ({
                    [this.saveKey]: tag,
                    [this.displayKey]: tag
                }));
            });
        },
        beforeDestroy () {
            window.removeEventListener('message', this.messageListener, false);
        },
        methods: {
            handleClick () {
                this.$refs.tagInput.focusInputer();
                if (!this.needsLogin || this.disabled) return;
                this.popupLogin();
            },
            /**
             * 过滤数据的回调函数
             *
             * @param {string} filterVal 当前过滤的文本
             * @param {string} filterKey 当前数据使用的 key
             * @param {Array} data 所有数据
             *
             * @return {Array} 过滤后的数据
             */
            filterCallback (filterVal, filterKey, data) {
                const filterData = [...data.filter(
                    item => {
                        const itemVal = item[filterKey].toLowerCase();
                        if (itemVal === filterVal) {
                            return Object.assign(item, { sortWeight: Number.MIN_SAFE_INTEGER });
                        }

                        const index = itemVal.indexOf(filterVal);
                        if (index > -1) {
                            return Object.assign(item, { sortWeight: index });
                        }
                    }
                )];

                return filterData.sort((x, y) => {
                    if (x.sortWeight <= y.sortWeight) {
                        return -1;
                    }
                    return 1;
                });
            },
            requestList () {
                const self = this;

                const host = location.host;
                const protocol = location.protocol;
                const typeList = ['rtx', 'email', 'all'];
                const prefix = host.indexOf(`.${window.GLOBAL_CONFIG.IED_DOMAIN}`) > -1
                    ? `http://o.${window.GLOBAL_CONFIG.IED_DOMAIN}/component/compapi/tof3/`
                    : host.indexOf(`.${window.GLOBAL_CONFIG.WOA_DOMAIN}`) > -1
                        ? `${protocol}//api.open.${window.GLOBAL_CONFIG.WOA_DOMAIN}/component/compapi/tof3/`
                        : `${protocol}//open.${window.GLOBAL_CONFIG.OA_DOMAIN}/component/compapi/tof3/`;
                const config = {
                    url: '',
                    data: {}
                };

                if (!typeList.includes(this.type)) {
                    return false;
                }

                switch (this.type) {
                    case 'rtx':
                        config.url = `${prefix}get_all_staff_info/`;
                        config.data = {
                            'query_type': 'simple_data',
                            'app_code': 'workbench'
                        };
                        break;
                    case 'email':
                        config.url = `${prefix}get_all_ad_groups/`;
                        config.data['query_type'] = undefined;
                        config.data = {
                            'app_code': 'workbench'
                        };
                        break;
                    case 'all':
                        config.url = `${prefix}get_all_rtx_and_mail_group/`;
                        config.data = {
                            'app_code': 'workbench'
                        };
                        break;
                    default:
                        break;
                }
                this.isLoading = true;
                this.ajaxRequest({
                    url: config.url,
                    jsonp: 'callback' + uuid(),
                    data: Object.assign(config.data),
                    success: function (res) {
                        self.isLoading = false;
                        if (res.result) {
                            res.data.map(val => {
                                self.renderList.push(val);
                            });
                        } else {
                            self.needsLogin = true;
                        }
                    },
                    error: function (error) {
                        console.error(error, 'retry...');
                        self.retry(config);
                    }
                });
            },
            messageListener ({ data = {} }) {
                if (data === null || typeof data !== 'object' || data.target !== this.$options.name) return;
                this.needsLogin = false;
                this.requestList();
                const loginWindow = window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_;
                if (!loginWindow) return;
                loginWindow.close();
                window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_ = null;
            },
            popupLogin () {
                if (window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_) return;
                this.$bkMessage({ message: this.t('bk.memberSelector.loginTips'), theme: 'error', limit: 1 });
                const width = 700;
                const height = 510;
                const { availHeight, availWidth } = window.screen;
                window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_ = window.open(getLoginUrl(), '_blank', `
                    width=${width},
                    height=${height},
                    left=${(availWidth - width) / 2},
                    top=${(availHeight - height) / 2},
                    channelmode=0,
                    directories=0,
                    fullscreen=0,
                    location=0,
                    menubar=0,
                    resizable=0,
                    scrollbars=0,
                    status=0,
                    titlebar=0,
                    toolbar=0,
                    close=0
                `);
                this.startCheckWindow();
            },
            startCheckWindow () {
                this.checkWindowTimer && clearTimeout(this.checkWindowTimer);
                this.checkWindowTimer = setTimeout(() => {
                    if (!window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_) {
                        clearTimeout(this.checkWindowTimer);
                        return;
                    }
                    if (window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_.closed) {
                        window._BK_MEMBER_SELECTOR_LOGIN_WINDOW_ = null;
                        return;
                    }
                    this.startCheckWindow();
                }, 300);
            },
            /**
             * 重新发送 http 请求，只在请求 http 失败时重试
             *
             * @param {Object} config 参数
             */
            retry (config) {
                const self = this;
                self.ajaxRequest({
                    url: config.url,
                    jsonp: 'callback' + uuid(),
                    data: Object.assign(config.data),
                    success: function (res) {
                        if (res.result) {
                            res.data.map(val => {
                                self.renderList.push(val);
                            });
                            self.isLoading = false;
                        } else {
                            self.isLoading = false;
                            self.$bkMessage({ message: res.message, theme: 'error', limit: 1 });
                        }
                    },
                    error: function (error) {
                        self.isLoading = false;
                        console.error(error);
                        const msg = (error && error.toString()) || self.t('bk.memberSelector.sysErrorMsg');
                        self.$bkMessage({ message: msg, theme: 'error', limit: 1 });
                    }
                });
            },

            ajaxRequest (params) {
                params = params || {};
                params.data = params.data || {};

                const callbackName = params.jsonp;
                const head = document.getElementsByTagName('head')[0];
                params.data['callback'] = callbackName;

                // 设置传递给后台的回调参数名
                const data = this.formatParams(params.data);
                const script = document.createElement('script');

                script.addEventListener('error', () => {
                    head.removeChild(script);
                    params.error && params.error();
                });
                head.appendChild(script);

                // 创建 jsonp 回调函数
                window[callbackName] = function (res) {
                    head.removeChild(script);
                    clearTimeout(script.timer);
                    window[callbackName] = null;
                    params.success && params.success(res);
                };

                // 发送请求
                script.src = params.url + '?' + data;
            },
            // 格式化参数
            formatParams (data) {
                const arr = [];
                for (const name in data) {
                    arr.push(encodeURIComponent(name) + '=' + encodeURIComponent(data[name]));
                }
                return arr.join('&');
            },
            tagTpl (node, ctx) {
                const parentClass = 'tag';
                const textClass = 'text';
                const avatarClass = 'avatar';

                let template;

                if (this.type === 'rtx') {
                    template = (
                            <div class={parentClass}>
                                <img class={avatarClass} src={`https://dayu.${window.GLOBAL_CONFIG.WOA_DOMAIN}/avatars/${node.english_name}/avatar.jpg`} />
                                <span class={textClass}>{node.english_name}</span>
                            </div>
                    );
                } else if (this.type === 'email') {
                    template = (
                            <div class={parentClass}>
                                <span class={textClass}>{node.FullName}</span>
                            </div>
                    );
                } else {
                    template = (
                            <div class={parentClass}>
                                <span class={textClass}>{node.english_name}</span>
                            </div>
                    );
                }
                return template;
            },
            tpl (node, ctx, highlightKeyword) {
                const parentClass = 'bk-selector-node bk-selector-member';
                const textClass = 'text';
                const imgClass = 'avatar';
                let template;

                switch (this.type) {
                    case 'rtx':
                        const child = `${highlightKeyword(node.english_name)} (${node.chinese_name})`;
                        template = (
                            <div class={parentClass}>
                                <img class={imgClass} src={`https://dayu.${window.GLOBAL_CONFIG.WOA_DOMAIN}/avatars/${node.english_name}/avatar.jpg`} />
                                <span
                                    class={textClass}
                                    domPropsInnerHTML={child}>
                                </span>
                            </div>
                        );
                        break;
                    case 'email':
                        template = (
                            <div class={parentClass}>
                                <span domPropsInnerHTML={highlightKeyword(node.FullName)} class={textClass}></span>
                            </div>
                        );
                        break;
                    case 'all':
                        template = (
                            <div class={parentClass}>
                                <span domPropsInnerHTML={highlightKeyword(node.english_name)} class={textClass}></span><span>-</span>
                                <span domPropsInnerHTML={node.chinese_name} class={textClass}></span>
                            </div>
                        );
                        break;
                    default:
                        break;
                }

                return template;
            },
            change (data) {
                this.$emit('change', data, this.selectedList);
                this.dispatch('bk-form-item', 'form-change');
            },
            select () {
                this.$emit('select', this.selectedList);
            },
            remove (data) {
                this.$emit('remove', this.selectedList);
            }
        }
    };
</script>

<style>
    @import './member-selector.css';
    .highlight-text {
        color: #3A84FF;
    }
</style>
