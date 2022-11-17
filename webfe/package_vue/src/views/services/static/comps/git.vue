<template lang="html">
  <div class="git-main">
    <div
      slot="loadingContent"
      class="middle"
    >
      <section
        v-for="(oauth, index) in oauth2Backends"
        :key="index"
      >
        <div class="middle-oauth-title">
          <h3>{{ titleInfo[oauth.name] }}</h3>
          <div class="ps-text-info">
            {{ infoMap[oauth.name] }}
          </div>
        </div>
        <div class="backend-wrapper">
          <ul class="backend-content-wrapper clearfix">
            <template v-if="isTokenExist">
              <li class="backend-list">
                <p class="correct-mark">
                  <i class="icon paasng-icon paasng-correct" />
                </p>
                <div class="show-content">
                  <!-- logo 无需格式化-->
                  <div class="img-wrapper">
                    <template v-if="oauth.name === 'tc_git'">
                      <img
                        class="devops-icon"
                        src="../../../../../static/images/devops.png"
                        alt=""
                      >
                      <div class="devops-icon-inner" />
                    </template>
                    <span
                      v-else
                      class="paasng-icon paasng-gitlab logo-icon"
                    />
                  </div>
                  <div class="desc-wrapper">
                    <h4 class="title">
                      {{ oauth.display_info.display_name }}
                    </h4>
                    <p class="text">
                      <span>{{ oauth.display_info.description }}</span>
                      <span
                        v-if="oauth.name === 'tc_git'"
                        class="scope"
                      >
                        {{ make_scope_readable(oauth.scope) }}
                      </span>
                    </p>
                  </div>
                </div>
              </li>
            </template>
            <template v-else>
              <li
                :class="['backend-list', 'no-impower']"
                @click.stop="auth_associate(oauth)"
              >
                <div class="show-content">
                  <div class="img-wrapper">
                    <span class="paasng-icon paasng-plus-thick logo-icon" />
                  </div>
                  <div class="desc-wrapper">
                    <h4 class="oauth-title">
                      <span> {{ $t('点击立即授权') }} </span>
                    </h4>
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
    import appBaseMixin from '@/mixins/app-base-mixin';
    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                loading: false,
                oauth2Backends: [
                    {
                        name: 'tc_git',
                        oauth_url: '',
                        display_info: {
                            display_name: this.$t('工蜂 Git'),
                            description: this.$t('腾讯内部 Git 源码托管系统')
                        },
                        scope: 'user:user'
                    }
                ],
                titleInfo: {
                    'tc_git': this.$t('工蜂 Git 授权')
                },
                infoMap: {
                    'tc_git': this.$t('授权蓝盾访问您的工蜂代码库信息，授权后可以通过蓝盾执行代码检查等CI操作')
                },
                isTokenExist: false
            };
        },
        created () {
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
            auth_associate (auth) {
                this.check_window_close(window.open(auth.oauth_url, this.$t('授权窗口'), 'height=600, width=600, top=200, left=400, toolbar=no, menubar=no, scrollbars=no, resizable=no, location=no, status=no'));
            },
            async check_window_close (win, sleepTime = 1000) {
                if (win.closed) {
                    this.fetchCiToken();
                } else {
                    await new Promise(resolve => {
                        setTimeout(resolve, sleepTime += 1000);
                    });
                    this.check_window_close(win, sleepTime);
                }
            }
        }
    };
</script>

<style lang="scss" scope>
    .middle-oauth-title {
        margin: 15px 0 19px 0;
        h3 {
            padding: 0;
            font-size: 14px;
            line-height: 40px;
            color: #55545a;
        }
        .ps-text-info {
            color: #666;
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
            position: relative;
            margin-right: 18px;
            width: 47px;
            height: 47px;
            .paasng-icon {
                font-size: 47px;
            }
            .devops-icon {
                height: 100%;
                border-radius: 50%;
                display: block;
                overflow: hidden;
                object-fit: cover;
            }
            .devops-icon-inner {
                position: absolute;
                top: 0;
                left: 0;
                bottom: -1px;
                right: -1px;
                background-image: url('../../../../../static/images/devops-inner.png');
                background-size: 100% 100%;
                background-repeat: no-repeat;
            }
        }
        .desc-wrapper {
            line-height: 16px;
            color: #63656E;
            font-size: 12px;
            .title {
                font-size: 14px;
                padding: 0;
                color: #313238;
                font-weight: bold;
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
    }
</style>
