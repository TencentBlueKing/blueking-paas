<template lang="html">
    <div class="git-main">
        <div slot="loadingContent" class="middle">
            <section v-for="(oauth, index) in oauth2Backends" :key="index">
                <div class="middle-oauth-title">
                    <h4>{{titleInfo[oauth.name]}}</h4>
                    <p class="ps-text-info">{{infoMap[oauth.name]}}</p>
                </div>
                <div class="backend-wrapper">
                    <ul class="backend-content-wrapper clearfix">
                        <template v-if="oauth.token_list.length">
                            <li class="backend-list"
                                v-for="(backendItem, backendIndex) in oauth.token_list"
                                :key="backendIndex"
                                :class="backendIndex > 1 ? 'set-mt' : ''">
                                <p class="correct-mark">
                                    <i class="icon paasng-icon paasng-correct"></i>
                                </p>
                                <div class="show-content">
                                    <!-- logo 无需格式化-->
                                    <div class="img-wrapper">
                                        <span class="paasng-icon paasng-logo logo-icon" v-if="oauth.name === 'tc_git'"></span>
                                        <img style="width: 47px; height: 47px;" v-else-if="oauth.name === 'github'" src="/static/images/github-logo.svg" alt="">
                                        <img style="width: 47px; height: 44px;" v-else-if="oauth.name === 'gitee'" src="/static/images/gitee-logo.svg" alt="">
                                        <span class="paasng-icon paasng-gitlab logo-icon" v-else></span>
                                    </div>
                                    <div class="desc-wrapper">
                                        <h4 class="title">
                                            {{oauth.display_info.display_name}}
                                        </h4>
                                        <p class="text">
                                            <span>{{oauth.display_info.description}}</span>
                                            <span class="scope" v-if="oauth.name === 'tc_git'">
                                                {{ make_scope_readable(backendItem.scope) }}
                                            </span>
                                        </p>
                                    </div>
                                </div>
                                <div class="hover-content">
                                    <bk-button theme="primary" @click="auth_associate(oauth.auth_url)"> {{ $t('重新授权') }} </bk-button>
                                    <bk-button theme="default" @click="disconnect(oauth, backendItem)"> {{ $t('取消授权') }} </bk-button>
                                </div>
                            </li>
                        </template>
                        <template v-if="oauth.associated">
                            <li
                                :class="['backend-list', 'no-impower', oauth.token_list.length > 1 ? 'set-mt' : '', oauth.token_list.length % 2 !== 0 ? 'set-ml' : '']" @click.stop="auth_associate(oauth.auth_url)">
                                <div class="show-content">
                                    <div class="img-wrapper">
                                        <span class="paasng-icon paasng-logo logo-icon" v-if="oauth.name === 'tc_git'"></span>
                                        <img style="width: 47px; height: 47px;" v-else-if="oauth.name === 'github'" src="/static/images/github-logo.svg" alt="">
                                        <img style="width: 47px; height: 44px;" v-else-if="oauth.name === 'gitee'" src="/static/images/gitee-logo.svg" alt="">
                                        <span class="paasng-icon paasng-plus-thick logo-icon" v-else></span>
                                    </div>
                                    <div class="desc-wrapper">
                                        <h4 class="oauth-title">
                                            {{oauth.display_info.display_name}}
                                            <!-- <span> {{ $t('点击立即授权') }} </span> -->
                                        </h4>
                                        <p class="text">
                                            <span>{{oauth.display_info.description}}</span>
                                        </p>
                                        <div class="btn-wrapper" v-if="oauth.display_info.auth_docs">
                                            <bk-button text theme="primary" @click.stop="openDocu(`${oauth.display_info.auth_docs}`)"> {{ $t('授权指引') }} </bk-button>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        </template>
                    </ul>
                </div>
            </section>
        </div>
    </div>
</template>

<script>
    export default {
        data () {
            return {
                loading: false,
                oauth2Backends: [],
                titleInfo: {
                    'tc_git': this.$t('工蜂 Git 授权'),
                    'bk_gitlab': this.$t('蓝鲸内部 GitLab 授权'),
                    'github': this.$t('Github 授权'),
                    'gitee': this.$t('Gitee 授权')
                },
                infoMap: {
                    'tc_git': this.$t('授权蓝鲸访问您的工蜂代码库信息，授权后蓝鲸仅获取工蜂仓库的只读权限'),
                    'bk_gitlab': this.$t('授权访问您的蓝鲸内部 GitLab 代码库信息，授权后蓝鲸仅获取仓库的只读权限'),
                    'github': this.$t('授权蓝鲸访问您的 Github 代码库信息，授权后蓝鲸将获取仓库的访问权限'),
                    'gitee': this.$t('授权蓝鲸访问您的 Gitee 代码库信息，授权后蓝鲸将获取仓库的访问权限')
                }
            };
        },
        created () {
            this.init();
        },
        methods: {
            make_scope_readable (scope) {
                if (scope === 'user:user') {
                    return this.$t('所有 API');
                }

                const pairs = scope.split(':');
                if (pairs[0] === 'project') {
                    return this.$t('项目: ') + pairs[1];
                } else if (pairs[0] === 'group') {
                    return this.$t('项目组: ') + pairs[1];
                } else {
                    return scope;
                }
            },
            auth_associate (authUrl) {
                this.check_window_close(window.open(authUrl, this.$t('授权窗口'), 'height=600, width=600, top=200, left=400, toolbar=no, menubar=no, scrollbars=no, resizable=no, location=no, status=no'));
            },
            disconnect (oauth, backendItem) {
                const url = `${BACKEND_URL}/api/oauth/backends/${oauth.name}/${backendItem.id}`;
                this.$http.delete(url).then((resp) => {
                    this.fetch_backend_status();
                });
            },
            fetch_backend_status () {
                this.loading = true;
                const url = `${BACKEND_URL}/api/oauth/backends/`;
                this.$http.get(url).then((resp) => {
                    (resp || []).forEach(item => {
                        const flag = item.token_list.length === 0 || item.display_properties.always_show_associated_panel;
                        this.$set(item, 'associated', flag);
                    });
                    resp = [...resp.sort((a, b) => {
                        const valueOne = a.name.toUpperCase();
                        const valueTwo = b.name.toUpperCase();
                        if (valueOne > valueTwo) {
                            return -1;
                        }
                        if (valueOne < valueTwo) {
                            return 1;
                        }
                        return 0;
                    })];
                    this.oauth2Backends = resp;
                    if (!resp.length) {
                        this.$emit('changeTips', 'git');
                    }
                }).finally(res => {
                    this.loading = false;
                    this.$emit('ready');
                });
            },
            init () {
                this.fetch_backend_status();
            },
            async check_window_close (win, sleepTime = 1000) {
                if (win.closed) {
                    this.fetch_backend_status();
                } else {
                    await new Promise(resolve => {
                        setTimeout(resolve, sleepTime += 1000);
                    });
                    this.check_window_close(win, sleepTime);
                }
            },
            openDocu (link) {
                window.open(link);
            }
        }
    };
</script>

<style lang="scss" scope>
    .middle-oauth-title {
        margin: 15px 0 19px 0;
        h4 {
            padding: 0;
            font-size: 14px;
            line-height: 19px;
            margin-bottom: 3px;
        }
        .ps-text-info {
            font-size: 12px;
            line-height: 16px;
            color: #979BA5;
        }
    }
    .backend-content-wrapper {
        overflow: hidden;
    }
    .backend-list {
        padding: 21.5px 0 21.5px 26px;
        position: relative;
        width: calc(50% - 10px);
        border-radius: 2px;
        border:1px solid rgba(220,222,229,1);
        box-sizing: border-box;
        float: left;
        &.set-mt {
            margin-top: 18px;
        }
        &:nth-child(2n) {
            float: right;
        }
        &:hover {
            border: 1px solid #3A84FF;

            .hover-content {
                opacity: 1;
            }

            .btn-wrapper {
                display: inline-block;
            }
        }
        &.no-impower {
            cursor: pointer;
            &.set-ml {
                margin-left: 18px;
            }
            .desc-wrapper {
                color: #C4C6CC;
                .title {
                    color: #C4C6CC;
                }
            }
            .img-wrapper {
                .logo-icon {
                    width: 100%;
                    -webkit-filter: grayscale(100%);
                    filter: grayscale(100%);
                    opacity: .4;
                }
            }
        }
        .correct-mark {
            position: absolute;
            right: 0;
            top: 0;
            width: 0;
            height: 0;
            border-top: 24px solid #2DCB56;
            border-left: 24px solid transparent;
            .icon {
                font-size: 17px;
                position: absolute;
                top: -25px;
                right: -2px;
                &:before {
                    color: #fff;
                }
            }
        }
        .show-content {
            font-size: 0;
            .img-wrapper, .desc-wrapper {
                display: inline-block;
                vertical-align: middle;
            }
        }
        .img-wrapper {
            margin-right: 18px;
            height: 47px;
            .paasng-icon {
                font-size: 47px;
            }
            .paas-logo {
                font-size: 46px;
            }
        }
        .desc-wrapper {
            line-height: 16px;
            color: #63656E;
            font-size: 12px;
            .title {
                // margin-bottom: 5px;
                font-size: 14px;
                padding: 0;
                color: #313238;
                font-weight: bold;
                // line-height: 19px;
            }
            .oauth-title {
                font-size: 14px;
                padding: 0;
                color: #C4C6CC;
                font-weight: bold;
                cursor: pointer;
            }
            .scope {
                margin-left: 10px;
                font-weight: 600;
            }
        }
        .btn-wrapper {
            display: none;
            position: absolute;
            right: 25px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 14px;
            line-height: 19px;
            a {
                &:first-child {
                    margin-right: 6px;
                }
            }
        }
        .hover-content {
            opacity: 0;
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:rgba(255,255,255,0.85);
            z-index: 10;
            text-align: center;
            line-height: 92px;
            transition: all 0.4s ease;
            .bk-primary {
                margin-right: 5px;
            }
        }
    }
</style>
