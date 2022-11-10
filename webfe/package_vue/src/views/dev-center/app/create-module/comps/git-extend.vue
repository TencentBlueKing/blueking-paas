<template>
    <div>
        <div class="establish-tab" style="display: block;" v-if="isAuth">
            <label class="form-label" style="font-weight: unset; padding-top: 0px; display:flex; justify-content: space-between;">
                <span> {{ $t('绑定项目源码仓库：') }} </span>
                <a @click="fetchMethod" style="cursor: pointer;"> {{ $t('刷新') }} </a>
            </label>
            <div id="shorter-loading-animate" class="mt10">
                <bk-select
                    v-model="selected"
                    :placeholder="$t('请选择')"
                    :clearable="false"
                    :searchable="true">
                    <bk-option
                        v-for="(option, optionIndex) in repoList"
                        :key="optionIndex"
                        :id="option.id"
                        :name="option.name">
                    </bk-option>
                </bk-select>
            </div>
        </div>
        <div class="lower-loading-animate establish-tab" style="padding-bottom: 9px" v-else>
            <paas-loading :loading="isLoading">
                <div slot="loadingContent" class="unbinded-prompt" v-if="gitControlType === 'tc_git'">
                    <span style="color: #ff3737;">{{ alertText }}</span>
                    {{ $t('首次使用工蜂，请先阅读') }}
                    <a :href="GLOBAL.DOC.TC_GIT_AUTH" target="_blank"> {{ $t('授权指引文档') }} </a>
                    <span style="float: right">
                        <a @click="auth_associate(authAddress, fetchMethod)" style="cursor: pointer;"> {{ $t('已阅读? 去关联') }} </a>
                    </span>
                </div>
                <div slot="loadingContent" class="unbinded-prompt tr" v-else>
                    <a @click="auth_associate(authAddress, fetchMethod)" style="cursor: pointer;"> {{ $t('去关联') }} </a>
                </div>
            </paas-loading>
        </div>
    </div>
</template>

<script>
    export default {
        props: {
            isAuth: {
                type: Boolean,
                default: false
            },
            isLoading: {
                type: Boolean,
                default: false
            },
            gitControlType: {
                type: String
            },
            alertText: {
                type: String
            },
            authAddress: {
                type: String
            },
            fetchMethod: {
                type: Function
            },
            repoList: {
                type: Array
            },
            selectedRepoUrl: {
                type: String
            }
        },
        data () {
            return {
                url: ''
            };
        },
        computed: {
            selected: {
                get: function () {
                    return this.url;
                },
                set: function (url) {
                    this.url = url;
                    this.$emit('update:selectedRepoUrl', url);
                }
            }
        },
        methods: {
            auth_associate (authUrl, callback) {
                this.check_window_close(
                    window.open(authUrl, this.$t('授权窗口'), 'height=600, width=600, top=200, left=400, toolbar=no, menubar=no, scrollbars=no, resizable=no, location=no, status=no'),
                    300, callback
                );
            },
            async check_window_close (win, sleepTime = 300, callback = () => undefined) {
                if (win.closed) {
                    callback();
                } else {
                    await new Promise(resolve => {
                        setTimeout(resolve, sleepTime);
                    });
                    this.check_window_close(win, sleepTime, callback);
                }
            }
        }
    };
</script>
