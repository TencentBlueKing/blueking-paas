<template lang="html">
  <div class="svn-main">
    <div slot="loadingContent">
      <div
        v-if="userid"
        class="code-content-wrapper"
      >
        <h4 class="head-title">
          {{ $t('蓝鲸SVN代码仓库') }}
        </h4>
        <p class="desc">
          {{ $t('如果应用选择使用SVN管理，蓝鲸将默认为该应用分配SVN仓库') }}
          <a
            href="https://tortoisesvn.net/downloads.html"
            target="_blank"
            style="display: none;"
          > {{ $t('查看SVN操作指引文档') }} </a>
          <a
            href="https://tortoisesvn.net/downloads.html"
            target="_blank"
          > {{ $t('下载SVN客户端') }} </a>
        </p>
        <div class="user-info-wrapper">
          <ul>
            <li class="user-list">
              <p class="title">
                {{ $t('用户名') }}
              </p>
              <div class="specific-desc">
                {{ userList.username }}
              </div>
            </li>
            <li class="user-list">
              <p class="title">
                {{ $t('密码') }}
              </p>
              <div class="specific-desc">
                {{ bkpaasUserId }}
                <a
                  id="getPassword"
                  v-bk-tooltips="$t('您将进行密码重置操作！')"
                  class="blue tooltip loadown-text"
                  href="javascript:"
                  @click="openPassword"
                >
                  <span v-dashed>{{ $t('忘记密码') }}</span>
                </a>
              </div>
              <div
                v-if="isopen"
                class="get-password"
              >
                <p style="line-height: 19px;">
                  {{ $t('验证码已发送至您的企业微信，请注意查收！') }}
                </p>
                <p style="margin: 18px 0 20px 0;">
                  <span class="password">
                    <input
                      v-model="verificationcode"
                      type="text"
                      class="password-text"
                      :placeholder="$t('请输入验证码')"
                    >
                    <bk-button
                      v-if="flag"
                      class="code-text"
                      theme="default"
                      :disabled="true"
                    >{{ timer }}s{{ $t('重新获取') }} </bk-button>
                    <bk-button
                      v-else
                      class="get-code-btn"
                      theme="default"
                      @click="getPassword(true)"
                    > {{ $t('重新获取') }} </bk-button>
                  </span>
                </p>
                <p style="font-size: 0;">
                  <bk-button
                    class="mr10"
                    theme="primary"
                    @click="resetPassword"
                  >
                    {{ $t('重置密码') }}
                  </bk-button>
                  <bk-button
                    theme="default"
                    @click="closePassword"
                  >
                    {{ $t('取消') }}
                  </bk-button>
                </p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
    import Clipboard from 'clipboard';

    export default {
        data () {
            return {
                name: this.$t('代码库管理'),
                isopen: false,
                timer: '60',
                // 倒计时
                flag: false,
                timeInterval: '',
                userList: '',
                bkpaasUserId: '',
                username: '',
                isCan: true,
                region: '',
                userid: '',
                verificationcode: '',
                isNew: '',
                phoneNumerLoading: true,
                loading: true,
                formLoading: false
            };
        },
        mounted () {
            const clipboard = new Clipboard('.password-submit');
            const me = this;
            clipboard.on('success', (e) => {
                me.$paasMessage({
                    theme: 'success',
                    message: this.$t('复制成功！')
                });
            });

            clipboard.on('error', (e) => {
                me.$paasMessage({
                    theme: 'error',
                    message: this.$t('复制失败！')
                });
            });
        },
        created () {
            // 获取用户信息
            this.$http.get(BACKEND_URL + '/api/accounts/userinfo/').then((response) => {
                this.userList = response;
                this.bkpaasUserId = this.userList.bkpaas_user_id.replace(/[A-Za-z0-9\-_]/g, '*');
                this.username = this.userList.username;
            }).finally(() => {
                this.loading = false;
                this.$emit('ready');
            });
            this.init();
        },
        methods: {
            initialize () {
                this.formLoading = true;

                const ParamsForCreation = {
                    'region': 'ieod'
                };
                // 调用post请求创建一个账户
                this.$http.post(BACKEND_URL + '/api/sourcectl/bksvn/accounts/', ParamsForCreation).then((response) => {
                    this.init();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('初始化蓝鲸SVN账号成功！')
                    });
                }, (res) => {
                    this.verificationcode = '';
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('初始化蓝鲸SVN账号失败！')
                    });
                }).then(() => {
                    this.closePassword();
                    clearInterval(this.timeInterval);
                    this.timer = 60;
                    this.isCan = true;
                    this.formLoading = false;
                });
            },
            openPassword () {
                if (this.isopen) {
                    return;
                }
                this.getPassword();
            },
            getPassword (isRetry) {
                // 接收值时打开输入框并获取密码
                if (isRetry) {
                    // 重新获取密码
                    this.timer = 60;
                    this.flag = true;
                } else {
                    if (!this.timer) {
                        this.timer = 60;
                    }
                    this.isopen = true;
                    this.flag = true;
                }

                if (this.flag) {
                    if (this.isCan) {
                        clearInterval(this.timeInterval);

                        // 验证码-生成并发送验证码到用户的手机
                        this.$http.post(BACKEND_URL + '/api/accounts/verification/generation/', { 'func': 'SVN' }).then((response) => {
                            this.phoneNumerLoading = false;
                        }, (response) => {
                            this.isopen = false;
                            this.closePassword();
                            clearInterval(this.timeInterval);
                            this.timer = 60;
                            this.isCan = true;
                            this.verificationcode = '';
                            this.$paasMessage({
                                theme: 'error',
                                message: this.$t('操作太频繁了，请稍后再试！')
                            });
                        });

                        this.isCan = false;
                    } else {
                        return;
                    }
                    this.timeInterval = setInterval(() => {
                        if (this.timer > 0) {
                            this.timer--;
                        } else {
                            this.flag = false;
                            this.isCan = true;
                        }
                    }, 1000);
                }
            },
            // 关闭密码框
            closePassword () {
                this.isopen = false;
                this.flag = false;
            },
            // 重置
            resetPassword () {
                if (this.verificationcode === '') {
                    this.$paasMessage({
                        limit: 1,
                        theme: 'error',
                        message: this.$t('请输入验证码！')
                    });
                    return false;
                }

                const paramsForReset = {
                    region: 'ieod',
                    verification_code: this.verificationcode
                };

                // 直接用put修改密码
                this.$http.put(BACKEND_URL + '/api/sourcectl/bksvn/accounts/' + this.userid + '/reset/', paramsForReset).then((response) => {
                    this.$paasMessage({
                        type: 'notify',
                        theme: 'success',
                        delay: 0,
                        title: this.$t('重置密码成功'),
                        message: `${this.$t('新密码为：')}${response.password} ${this.$t('刷新页面后将无法查看，请妥善保存')}`
                    });
                    this.closePassword();
                    clearInterval(this.timeInterval);
                    this.timer = 60;
                    this.isCan = true;
                }, (res) => {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('验证码错误！')
                    });
                }).then(() => {
                    this.verificationcode = '';
                });
            },
            init () {
                // 判断是否存在svn账户
                this.$http.get(BACKEND_URL + '/api/sourcectl/bksvn/accounts/').then((response) => {
                    const dataRes = response;
                    if (dataRes.length !== 0) {
                        this.userid = dataRes[0].id;
                    }
                });
                if (!this.userid) {
                    this.$emit('changeTips', 'svn');
                }
            }
        }
    };
</script>

<style lang="css" scoped>
    .password-submit.renew {
        margin: 0;
        border-radius: 0 2px 2px 0;
    }
    .password-submit, .password-reset {
        margin-left: 0;
    }
    .immediately.check.password-submit {
        margin-top: 0;
        border-radius: 0 2px 2px 0;
    }
    .password {
        color: #666;
        font-size: 14px;
    }
    .get-password {
        transition: all .5s;
    }
    .noallowed {
        cursor: not-allowed;
    }
    .bk-loading2 {
        display: inline-block;
    }
    .form-loading {
        margin: 10px 0;
        height: 42px;
        line-height: 42px;
        font-size: 14px;
    }
    .form-loading img {
        position: relative;
        top: 2px;
    }
    .password-text {
        float: left;
    }

    #getPassword {
        vertical-align: middle;
        line-height: 20px;
    }
    .coding {
        padding: 58px 0 956px 0;
        line-height: 36px;
        text-align: center;
        color: #666;
    }
    .coding h2 {
        line-height: 46px;
        font-size: 22px;
        color: #333;
    }
    a.code-a {
        padding-right: 16px;
        line-height: 34px;
        color: #3A84FF;
    }
    .paasng-angle-double-right {
        font-size: 12px;
        font-weight: bold;
    }
    .code-btn {
        width: 198px;
        height: 42px;
        line-height: 42px;
        font-size: 14px;
    }
    .middle h1 {
        margin-bottom: 16px;
        padding-top: 10px;
        line-height: 36px;
        font-size: 18px;
        color: #333;
        border-bottom: solid 1px #eaeeee;
        font-weight: normal;
    }
    .middle-code {
        line-height: 34px;
        color: #666;
    }
    .middle-text1 {
        display: inline-block;
        width: 100px;
        padding-right: 12px;
        line-height: 40px;
        color: #333;
        font-weight: bold;
    }
    .middle-code .blue {
        display: inline-block;
        line-height: 40px;
    }
    .pr10 {
        padding-right: 10px;
    }
    .pb856 {
        padding-bottom: 856px;
    }
    .get-password {
        position: absolute;
        top: 33px;
        right: 23px;
        padding: 32px 25px 32px 30px;
        border-radius: 2px;
        background:rgba(255,255,255,1);
        box-shadow:0px 3px 6px 0px rgba(0,0,0,0.1);
        border:1px solid rgba(220,222,229,1);
        color: #63656E;
    }
    .get-password.open {
        display: block;
    }
    .get-password .password {
        display: inline-block;
        font-size: 0;
    }
    .get-password .password .get-code-btn {
        border-radius: 0 2px 2px 0;
        border: 1px solid #3a84ff;
        color: #3a84ff;
    }
    .get-password .password .code-text {
        padding: 0;
        min-width: 100px;
        background: rgba(196,198,204,1);
        color: #fff;
        border: none;
        border-radius: 0 2px 2px 0;
    }
    .password-text {
        padding: 0 10px;
        width: 215px;
        height: 32px;
        line-height: 30px;
        border-radius: 2px 0 0 2px;
        border: solid 1px #c4c6cc;
        border-right: none;
        font-size: 14px;
        transition: all .5s;
    }
    .password-text:focus {
        outline: none;
        border-color: #c4c6cc;
        box-shadow: 0 2px 4px #eeeeee;
    }
    .password-wait {
        display: inline-block;
        padding: 0 15px;
        height: 36px;
        line-height: 36px;
        background: #ccc;
        color: #fff;
        font-size: 14px;
    }
    .password-submit,.password-reset {
        margin: 10px 10px 0 0;
        width: 90px;
        height: 34px;
        font-weight: normal;
        line-height: 34px;
        border: solid 1px #3A84FF;
        font-size: 14px;
    }
    .password-reset{
        color: #ccc;
        background: #fff;
        border: solid 1px #ccc;
    }
    .password-reset:hover{
        background: #ccc;
        color: #fff;
    }
    .get-password:after {
        content: "";
        position: absolute;
        top: -7px;
        right: 27px;
        width: 12px;
        height: 7px;
        background: url(/static/images/user-icon2.png) no-repeat;
    }
    .get-width {
        display: inline-block;
        width: 92px;
    }
    .immediately{
        width: 90px;
        height: 36px;
        line-height: 36px;
        color: #fff;
        text-align: center;
        background: #3A84FF;
        font-weight: bold;
        border-radius: 2px;
        transition: all .5s;
        margin-left: 10px;
    }
    .immediately:hover {
        background: #4e93d9
    }
    .immediately img{
        position: relative;
        top: 10px;
        margin-right: 5px;
        vertical-align: top;
    }
</style>
<style lang="scss" scoped>
    .code-content-wrapper {
        margin-top: 37px;
        .title {
            margin-bottom: 3px;
            padding: 0;
            font-size: 14px;
            font-weight: bold;
            color: rgba(49,50,56,1);
            line-height: 19px;
        }
        .head-title {
            margin-bottom: 3px;
            padding: 0;
            font-size: 14px;
            font-weight: bold;
            color: #5d6075;
            line-height: 19px;
        }
        .desc {
            margin-bottom: 19px;
            font-size: 12px;
            color: rgba(151,155,165,1);
            line-height: 16px;
            a {
                margin: 0 6px;
                &:last-child {
                    margin: 0;
                }
            }
        }
    }
    .user-info-wrapper {
        width: 100%;
        border-radius:2px;
        border:1px solid rgba(220,222,229,1);
        .user-list {
            position: relative;
            padding: 0 11px;
            font-size: 14px;
            color: #313238;
            border-bottom: 1px solid #DCDEE5;
            &:last-child {
                border-bottom: none;
            }
            .title {
                padding-right: 12px;
                position: absolute;
                left: 0;
                top: 0;
                width: 99px;
                line-height: 41px;
                border-right: 1px solid #DCDEE5;
                text-align: right;
            }
            .specific-desc {
                position: relative;
                padding-left: 22px;
                margin-left: 99px;
                line-height: 41px;
                color: #63656E;
                .loadown-text {
                    position: absolute;
                    font-size: 12px;
                    right: 20px;
                    line-height: 41px !important;
                }
            }
        }
    }
</style>
