<template lang="html">
  <div class="mobile-config-part">
    <div class="ps-top-card">
      <p class="main-title">
        {{ $t('移动端配置') }}
      </p>
      <p class="desc">
        {{ $t('开启移动端配置允许通过微信访问蓝鲸应用。使用前请先阅读') }}
        <a
          :href="GLOBAL.DOC.APP_ENTRY_INTRO"
          target="blank"
        > {{ $t('详细使用说明') }} </a>
      </p>
    </div>

    <div
      v-if="isInitLoading"
      class="result-table-content"
    >
      <paas-loading :loading="isInitLoading">
        <div class="ps-loading-placeholder" />
      </paas-loading>
    </div>
    <div
      v-else-if="mobileConfig.canReleaseToMobile"
      class="content"
    >
      <div class="controller">
        <div
          v-for="key of ['stag', 'prod']"
          :key="key"
          class="switch-wrapper ps-card"
        >
          <div class="header">
            <span class="title">{{ key === 'stag' ? $t('预发布环境') : $t('生产环境') }}</span>
            <div
              class="action"
              @click.stop.prevent="onToggleChange(key)"
            >
              <bk-switcher
                v-model="mobileConfig[key].is_enabled"
              />
            </div>
          </div>
          <div
            class="content"
            style="height: 140px;"
          >
            <template v-if="mobileConfig[key].is_enabled">
              <wx-qiye-qrcode
                style="border: 1px solid #F0F1F5; border-radius: 2px;"
                :url="mobileConfig[key].access_domain"
                :size="96"
              />
              <div class="guide">
                <div class="path">
                  <strong>{{ $t('微信请访问') }}:</strong>
                  <p>
                    <span> {{ $t('微信') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span> {{ $t('通讯录') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span> {{ $t('腾讯企业号') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span>{{ key === 'stag' ? `${GLOBAL.HELPER.name}测试` : `${GLOBAL.HELPER.name}` }}</span>
                  </p>
                </div>
                <div class="path">
                  <strong>{{ $t('企业微信请访问') }}:</strong>
                  <p>
                    <span> {{ $t('企业微信') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span> {{ $t('工作台') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span> {{ $t('更多') }} </span>
                    <i class="paasng-icon paasng-angle-right" />
                    <span>{{ key === 'stag' ? `${GLOBAL.HELPER.name}测试` : `${GLOBAL.HELPER.name}` }}</span>
                  </p>
                </div>
              </div>
            </template>
            <template v-else>
              <div
                class="ps-guide-box"
                style="margin-top: 30px;"
              >
                {{ $t('如需在微信 / 企业微信进行访问') }} <br> {{ $t('请先开启') }}{{ key === 'stag' ? $t('预发布环境') : $t('生产环境') }}
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
    <div
      v-else
      class="content"
    >
      <p class="description">
        {{ $t('该功能暂未开放，如需体验请联系') }}
        <a
          v-if="GLOBAL.HELPER.href"
          :href="GLOBAL.HELPER.href"
        >{{ GLOBAL.HELPER.name }}</a>
        <span v-else> {{ $t('管理员') }} </span>
      </p>
    </div>
  </div>
</template>

<script>
    import wxQiyeQrcode from '@/components/ui/Qrcode';

    export default {
        components: {
            wxQiyeQrcode
        },
        data () {
            return {
                isInitLoading: false,
                mobileConfig: {
                    stag: {
                        is_enabled: false
                    },
                    prod: {
                        is_enabled: false
                    },
                    canReleaseToMobile: false,
                    errMsg: `${this.$t('请联系')}${this.GLOBAL.HELPER.name}${this.$t('开启权限')}!`
                },
                appCode: ''
            };
        },
        watch: {
            '$route.params': function () {
                this.appCode = this.$route.params.id;
                this.init();
            }
        },
        mounted () {
            this.appCode = this.$route.params.id;
            this.init();
        },
        methods: {
            init: function () {
                this.loadMobileConfig();
            },
            loadMobileConfig: function () {
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/mobile_config/`;
                this.isInitLoading = true;
                this.$http.get(url).then(
                    res => {
                        this.mobileConfig = Object.assign(this.mobileConfig, res, { canReleaseToMobile: true });
                    },
                    res => {
                        this.mobileConfig.canReleaseToMobile = false;
                    }
                ).finally(res => {
                    this.isInitLoading = false;
                    this.$emit('data-ready', 'mobile-config');
                });
            },
            onToggleChange: function (env) {
                if (!this.mobileConfig.canReleaseToMobile) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.mobileConfig.errMsg
                    });
                    return false;
                }
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/envs/${env}/mobile_config/`;
                const isEnabled = !this.mobileConfig[env].is_enabled;
                this.$http.post(url, { is_enabled: isEnabled }).then(res => {
                    this.mobileConfig[env] = res;
                }).catch(err => {
                    this.$paasMessage({
                        theme: 'error',
                        message: err.detail
                    });
                    this.mobileConfig[env].is_enabled = !isEnabled;
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    .mobile-config-part {
        .content {
            display: flex;

            .description {
                font-size: 13px;
                padding: 15px 0;
                width: 35%;
            }

            .controller {
                width: 100%;
                display: flex;
                padding: 20px 0px 0px 0;
                justify-content: space-between;

                .switch-wrapper {
                    width: 48.6%;

                    .content {
                        display: flex;
                    }
                    .guide {
                        display: inline-block;
                        margin-left: 20px;

                        strong {
                            font-size: 12px;
                            font-weight: bold;
                            color: #63656E;
                            margin-bottom: 10px;
                            display: inline-block;
                        }
                    }
                    .path {
                        padding: 5px 0px 10px 0;
                        font-size: 12px;
                        color: #52525d;
                        line-height: 1;

                        .paasng-icon {
                            font-size: 12px;
                            vertical-align: middle;
                        }

                        span {
                            color: #3A84FF;
                            vertical-align: middle;
                        }
                    }
                }
            }
        }

        .wx-qrcode {
            width: 87px;
            height: 87px;
        }
    }
    .action {
        position: relative;
        &::after {
            content: '';
            position: relative;
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            bottom: 0;
            margin: auto;
            z-index: 10;
            cursor: pointer;
        }
    }
</style>
