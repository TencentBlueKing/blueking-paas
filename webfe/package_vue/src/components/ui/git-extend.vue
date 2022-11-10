<template>
    <div>
        <div class="establish-tab" style="display: block;" v-if="isAuth">
            <div id="shorter-loading-animate" class="mt10">
                <div class="form-label"> {{ $t('代码仓库') }} </div>
                <bk-select
                    v-model="selected"
                    :placeholder="$t('请选择')"
                    :clearable="false"
                    :searchable="true"
                    :loading="isLoading"
                    :key="selected"
                    @selected="selectedFun">
                    <bk-option
                        v-for="(option, index) in repoList"
                        :key="index"
                        :id="option.id"
                        :name="option.name">
                    </bk-option>
                </bk-select>
                <label class="pl10" style="font-weight: unset; padding-top: 0px; font-size: 12px">
                    <a @click="fetchMethod" style="cursor: pointer;"> {{ $t('刷新') }} </a>
                </label>
            </div>
        </div>
        <div class="lower-loading-animate establish-tab" style="padding-bottom: 9px" v-else>
            <paas-loading :loading="isLoading">
                <div slot="loadingContent" class="unbinded-prompt" v-if="gitControlType === 'tc_git' || gitControlType === 'github' || gitControlType === 'gitee'">
                    <span style="color: #ff3737;">{{ alertText }}</span>
                    <span v-if="gitControlType === 'tc_git'">{{ $t('首次使用工蜂，请先阅读') }}</span>
                    <span v-else-if="gitControlType === 'github'">{{ $t('首次使用Github，请先阅读') }}</span>
                    <span v-else>{{ $t('首次使用Gitee，请先阅读') }}</span>
                    <a :href="authDocs" target="_blank"> {{ $t('授权指引文档') }} </a>
                    <span style="float: right">
                        <a @click="auth_associate(authAddress, fetchMethod)" style="cursor: pointer;"> {{ $t('已阅读') }}? {{ $t('去关联') }} </a>
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
            authDocs: {
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
                url: this.selectedRepoUrl
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
                    this.$emit('change', url);
                }
            }
        },
        watch: {
            selectedRepoUrl (value) {
                this.url = value;
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
            },

            selectedFun (value) {
                this.$emit('selected', value);
            }
        }
    };
</script>

<style lang="scss">
    #shorter-loading-animate {
        display: flex;
        align-items: center;
        .form-label{
            width: 90px;
            text-align: right;
            margin-right: 10px;
            &::after {
                height: 8px;
                line-height: 1;
                content: '*';
                color: #EA3636;
                font-size: 12px;
                display: inline-block;
                vertical-align: middle;
                padding-left: 5px;
            }
        }
        .bk-select {
            width: 520px;
            height: 42px;
            .bk-select-name {
                height: 40px;
            }

            .bk-select-angle {
                top: 10px;
            }

            .bk-select-loading {
                top: 10px;
            }

            &.is-unselected:before {
                line-height: 40px;
            }

            .bk-select-name {
                line-height: 40px;
            }
        }
    }
</style>
