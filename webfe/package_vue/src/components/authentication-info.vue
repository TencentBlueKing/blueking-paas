<template>
  <div
    v-if="canViewSecret"
    class="basic-info-item"
  >
    <div class="title">
      {{ $t('鉴权信息') }}
    </div>
    <div class="info">
      {{ $t('在调用蓝鲸云 API 时需要提供应用鉴权信息。使用方法请参考：') }} <a
        :href="GLOBAL.DOC.APIGW_USER_API"
        target="_blank"
      > {{ $t('API调用指引') }} </a>
    </div>
    <div class="content">
      <div class="content-item">
        <label v-if="platformFeature.APP_ID_ALIAS">
          <p class="title-p top">app id</p>
          <p class="title-p bottom tip"> {{ $t('别名') }}：bk_app_code </p>
        </label>
        <label v-else>
          <p class="title-p mt15">bk_app_code</p>
        </label>
        <div class="item-practical-content">
          {{ curAppInfo.application.code }}
        </div>
      </div>
      <div class="content-item">
        <label v-if="platformFeature.APP_ID_ALIAS">
          <p class="title-p top">app secret</p>
          <p class="title-p bottom tip"> {{ $t('别名') }}：bk_app_secret </p>
        </label>
        <label v-else>
          <p class="title-p mt15">bk_app_secret</p>
        </label>
        <div class="item-practical-content">
          <span>{{ appSecretText }}</span>
          <span
            v-if="!appSecret"
            v-bk-tooltips="platformFeature.VERIFICATION_CODE ? $t('验证查看') : $t('点击查看')"
            class="paasng-icon paasng-eye"
            style="cursor: pointer;"
            @click="onSecretToggle"
          />
          <div
            v-if="isAcceptSMSCode"
            class="accept-vcode"
          >
            <p> {{ $t('验证码已发送至您的企业微信，请注意查收！') }} </p>
            <p style="display: flex;align-items: center;">
              <b> {{ $t('验证码：') }} </b>
              <bk-input
                v-model="appSecretVerificationCode"
                type="text"
                :placeholder="$t('请输入验证码')"
                style="width: 200px; margin-right: 10px;"
              />
              <bk-button
                v-if="appSecretTimer !== 0"
                theme="default"
                :disabled="true"
              >
                {{ appSecretTimer }}s&nbsp;{{ $t('后重新获取') }}
              </bk-button>
              <bk-button
                v-else
                theme="default"
                @click="sendMsg"
              >
                {{ $t('重新获取') }}
              </bk-button>
            </p>
            <p style="display: flex;">
              <b style="visibility: hidden;"> {{ $t('验证码：') }} </b>
              <bk-button
                theme="primary"
                style="margin-right: 10px;"
                @click="getAppSecret"
              >
                {{ $t('提交') }}
              </bk-button>
              <bk-button
                theme="default"
                @click="isAcceptSMSCode = false"
              >
                {{ $t('取消') }}
              </bk-button>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
    import appBaseMixin from '@/mixins/app-base-mixin';
    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                appSecretVerificationCode: '',
                appSecretTimer: 0,
                showingSecret: false,
                phoneNumerLoading: true,
                isAcceptSMSCode: false,
                appSecret: null
            };
        },
        computed: {
            canViewSecret () {
                return this.curAppInfo.role.name !== 'operator';
            },
            platformFeature () {
                console.warn(this.$store.state.platformFeature);
                return this.$store.state.platformFeature;
            },
            appSecretText () {
                if (this.appSecret && this.showingSecret) {
                    return this.appSecret;
                } else {
                    return '************';
                }
            },
            userFeature () {
                return this.$store.state.userFeature;
            },
            curPluginInfo () {
                return this.$store.state.curPluginInfo;
            }
        },
        mounted () {
            console.log('curPluginInfo', this.curPluginInfo);
        },
        methods: {
            onSecretToggle () {
                if (!this.userFeature.VERIFICATION_CODE) {
                    const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
                    this.$http.post(url, { verification_code: '' }).then(
                        res => {
                            this.isAcceptSMSCode = false;
                            console.log('res--appSecret', res);
                            this.appSecret = res.app_secret;
                            this.showingSecret = true;
                        },
                        res => {
                            this.$paasMessage({
                                theme: 'error',
                                message: this.$t('验证码错误！')
                            });
                        }
                    );
                    return;
                }
                if (this.appSecret) {
                    this.showingSecret = !this.showingSecret;
                    return;
                }
                this.phoneNumerLoading = true;
                this.sendMsg().then(() => {
                    this.phoneNumerLoading = false;
                    this.isAcceptSMSCode = true;
                }).catch(_ => {
                    this.isAcceptSMSCode = false;
                    this.appSecretTimer = 0;
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请求失败，请稍候重试')
                    });
                });
            },
            getAppSecret () {
                if (this.appSecretVerificationCode === '') {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: this.$t('请输入验证码！')
                    });
                    return;
                }
                const form = {
                    verification_code: this.appSecretVerificationCode
                };
                const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
                this.$http.post(url, form).then(
                    res => {
                        this.isAcceptSMSCode = false;
                        this.appSecret = res.app_secret;
                        this.showingSecret = true;
                    },
                    res => {
                        this.$paasMessage({
                            theme: 'error',
                            message: this.$t('验证码错误！')
                        });
                    }
                ).then(() => {
                    this.appSecretVerificationCode = '';
                });
            },

            sendMsg () {
                // 硬编码，需前后端统一
                return new Promise((resolve, reject) => {
                    this.resolveLocker = resolve;
                    if (this.appSecretTimer > 0) {
                        this.resolveLocker();
                        return;
                    }
                    const url = `${BACKEND_URL}/api/accounts/verification/generation/`;

                    this.appSecretTimer = 60;
                    this.$http.post(url, { func: 'GET_APP_SECRET' }).then(
                        res => {
                            this.appSecretVerificationCode = '';
                            this.resolveLocker();
                            if (!this.appSecretTimeInterval) {
                                this.appSecretTimeInterval = setInterval(() => {
                                    if (this.appSecretTimer > 0) {
                                        this.appSecretTimer--;
                                    } else {
                                        clearInterval(this.appSecretTimeInterval);
                                        this.appSecretTimeInterval = undefined;
                                    }
                                }, 1000);
                            }
                        },
                        res => {
                            this.appSecretVerificationCode = '';
                            reject(new Error(this.$t('请求失败，请稍候重试！')));
                        }
                    );
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
  .basic-info-item {
      margin-bottom: 35px;
      .title {
          color: #313238;
          font-size: 14px;
          font-weight: bold;
          line-height: 1;
          margin-bottom: 5px;
      }
      .info {
          color: #979ba5;
          font-size: 12px;
      }
      .content {
          margin-top: 20px;
          border: 1px solid #dcdee5;
          border-radius: 2px;
          &.no-border {
              border: none;
          }
          .info-special-form:nth-child(2) {
              position: relative;
              top: -4px;
          }
          .info-special-form:nth-child(3) {
              position: relative;
              top: -8px;
          }
          .info-special-form:nth-child(4) {
              position: relative;
              top: -12px;
          }
          .info-special-form:nth-child(5) {
              position: relative;
              top: -16px;
          }
          .item-content {
              padding: 0 10px 0 25px;
              height: 42px;
              line-height: 42px;
              border-right: 1px solid #dcdee5;
              border-bottom: 1px solid #dcdee5;
          }

          .item-logn-content{
              padding: 20px 10px 0 25px;
              height: 105px;
              border-right: 1px solid #dcdee5;
              border-top: 1px solid #dcdee5;
              .tip {
                  font-size: 12px;
                  color: #979BA5;
              }
          }
          .title-label {
              display: inline-block;
              width: 180px;
              height: 42px;
              line-height: 42px;
              text-align: center;
              border: 1px solid #dcdee5;
          }

          .logo{
              height: 105px;
              line-height: 105px;
          }

          .plugin-info {
              height: 460px;
              padding-top: 20px;
          }

          .content-item {
              position: relative;
              height: 60px;
              line-height: 60px;
              border-bottom: 1px solid #dcdee5;
              label {
                  display: inline-block;
                  position: relative;
                  top: -1px;
                  width: 180px;
                  height: 60px;
                  border-right: 1px solid #dcdee5;
                  color: #313238;
                  vertical-align: middle;
                  .basic-p {
                      padding-left: 30px;
                  }
                  .title-p {
                      line-height: 30px;
                      text-align: center;
                      &.tip {
                          font-size: 12px;
                          color: #979ba5;
                      }
                  }
                  .top {
                      transform: translateY(5px);
                  }
                  .bottom {
                      transform: translateY(-5px);
                  }
              }
              .item-practical-content {
                  display: inline-block;
                  padding-left: 20px;
                  max-width: calc(100% - 180px);
                  text-overflow: ellipsis;
                  overflow: hidden;
                  white-space: nowrap;
                  vertical-align: top;

                  .edit-input {
                      display: inline-block;
                      position: relative;
                      top: -1px;
                  }

                  .edit-button {
                      display: inline-block;
                      position: absolute;
                      right: 10px;
                  }

                  .edit {
                      position: relative;
                      color: #63656e;
                      font-weight: bold;
                      cursor: pointer;
                      &:hover {
                          color: #3a84ff;
                      }
                  }
              }
          }
          .content-item:last-child {
              border-bottom: none;
          }
          .pre-release-wrapper,
          .production-wrapper {
              display: inline-block;
              position: relative;
              width: 430px;
              border: 1px solid #dcdee5;
              border-radius: 2px;
              vertical-align: top;
              &.has-left {
                  left: 12px;
              }
              .header {
                  height: 41px;
                  line-height: 41px;
                  border-bottom: 1px solid #dcdee5;
                  background: #fafbfd;
                  .header-title {
                      margin-left: 20px;
                      color: #63656e;
                      font-weight: bold;
                      float: left;
                  }
                  .switcher-wrapper {
                      margin-right: 20px;
                      float: right;
                      .date-tip {
                          margin-right: 5px;
                          line-height: 1;
                          color: #979ba5;
                          font-size: 12px;
                      }
                  }
              }
              .ip-content {
                  padding: 14px 24px 14px 14px;
                  height: 138px;
                  overflow-x: hidden;
                  overflow-y: auto;
                  .ip-item {
                      display: inline-block;
                      margin-left: 10px;
                      vertical-align: middle;
                  }
                  .no-ip {
                      position: absolute;
                      top: 50%;
                      left: 50%;
                      transform: translate(-50%, -50%);
                      text-align: center;
                      font-size: 12px;
                      color: #63656e;
                      p:nth-child(2) {
                          margin-top: 2px;
                      }
                  }
              }
          }
          .ip-tips {
              margin-top: 7px;
              color: #63656e;
              font-size: 12px;
              i {
                  color: #ff9c01;
              }
          }
      }
  }
  .accept-vcode {
        position: relative;
        top: -6px;
        margin-top: 15px;
        padding: 20px;
        background: #fff;
        box-shadow: 0 2px 4px #eee;
        border: 1px solid #eaeeee;
        color: #666;
        z-index: 1600;

        .bk-loading2 {
            display: inline-block;
        }

        b {
            color: #333;
        }

        p {
            line-height: 30px;
            padding-bottom: 10px;
        }

        .password-text {
            padding: 0 10px;
            margin-right: 10px;
            width: 204px;
            height: 34px;
            line-height: 34px;
            border-radius: 2px 0 0 2px;
            border: solid 1px #e1e6e7;
            font-size: 14px;
            transition: all .5s;
        }

        .password-text:focus {
            outline: none;
            border-color: #e1e6e7;
            box-shadow: 0 2px 4px #eee;
        }

        .password-wait {
            background: #ccc;
            color: #fff;
            display: inline-block;
        }

        .password-submit,
        .password-reset {
            margin: 10px 10px 0 0;
            width: 90px;
            height: 34px;
            line-height: 34px;
            border: solid 1px #3A84FF;
            font-size: 14px;
            font-weight: normal;
        }

        .password-reset {
            color: #ccc;
            background: #fff;
            border: solid 1px #ccc;
        }

        .password-reset:hover {
            background: #ccc;
            color: #fff;
        }

        .get-password:after {
            content: "";
            position: absolute;
            top: -10px;
            left: 147px;
            width: 16px;
            height: 10px;
            background: url(/static/images/user-icon2.png) no-repeat;
        }

        .immediately {
            margin-left: 10px;
            width: 90px;
            height: 36px;
            line-height: 36px;
            color: #fff;
            text-align: center;
            background: #3A84FF;
            font-weight: bold;
            border-radius: 2px;
            transition: all .5s;
        }

        .immediately:hover {
            background: #4e93d9
        }

        .immediately img {
            position: relative;
            top: 10px;
            margin-right: 5px;
            vertical-align: top;
        }
    }
</style>
