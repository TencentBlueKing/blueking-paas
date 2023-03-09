<template>
  <div id="app">
    <paas-header />
    <div
      style="min-height: calc(100% - 70px); overflow: auto;"
      :class="{ 'plugin-min-width': isPlugin }"
    >
      <router-view />
    </div>
    <paas-footer v-if="$route.meta.showPaasFooter" />
    <div
      v-if="showLoginModal"
      class="login-dialog"
    >
      <div class="hole-bg" />
      <iframe
        :src="loginURL"
        scrolling="no"
        border="0"
        width="500"
        height="400"
        :class="GLOBAL.APP_VERSION !== 'te' ? 'small' : ''"
      />
    </div>
  </div>
</template>

<script>
    import { bus } from '@/common/bus';
    import paasHeader from '@/components/paas-header';
    import paasFooter from '@/components/paas-footer';

    export default {
        components: {
            paasHeader,
            paasFooter
        },
        data () {
            const loginCallbackURL = `${window.location.origin}/static/login_success.html?is_ajax=1`;
            const loginURL = `${window.GLOBAL_CONFIG.LOGIN_SERVICE_URL}/plain/?size=big&app_code=1&c_url=${loginCallbackURL}`;
            return {
                userInfo: {},
                loginURL: loginURL,
                showLoginModal: false,
                isPlugin: false
            };
        },
        computed: {
            isGray () {
                return ['myApplications', 'appLegacyMigration'].includes(this.$route.name);
            }
        },
        watch: {
            '$route': {
                handler (value) {
                    this.isPlugin = value.path.includes('/plugin-center');
                },
                immediate: true
            }
        },
        created () {
            bus.$on('show-login-modal', () => {
                this.showLoginModal = true;
            });
            bus.$on('close-login-modal', () => {
                this.showLoginModal = false;
                window.location.reload();
            });
        },
        methods: {
            hideLoginModal () {
                this.showLoginModal = false;
            }
        }
    };
</script>

<style lang="scss">
    @import './assets/css/patch.scss';
    @import './assets/css/ps-style.scss';

    .gray-bg {
        background: #fafbfd;
    }

    .login-dialog {
        position: fixed;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        z-index: 99999;
    }

    .login-dialog .hole-bg {
        position: fixed;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, .7);
    }

    .login-dialog .close-btn {
        position: absolute;
        left: 50%;
        z-index: 10002;
        margin-left: 220px;
        top: 50%;
        margin-top: -235px;
        width: 16px;
        height: 16px;
        background: #FFF;
        border-radius: 8px;
        text-align: center;
        z-index: 10002;
        cursor: pointer;
    }

    .login-dialog .close-btn:hover {
        box-shadow: 0 0 10px rgba(255, 255, 255, .5);
    }

    .login-dialog .close-btn img {
        width: 8px;
        margin-top: 0;
        display: inline-block;
        position: relative;
        top: -1px;
    }

    .login-dialog iframe {
        display: block;
        background: #FFF;
        border: 0;
        width: 700px;
        height: 510px;
        margin: -225px auto 0;
        top: 50%;
        position: relative;
        z-index: 10002;
        &.small {
            width: 400px;
            height: 400px;
        }
    }

    .notice {
        position: fixed;
        left: 0px;
        top: 0px;
        width: 100%;
        z-index: 1001;
        text-align: center;
        line-height: 32px;
        background-color: #ff9600;
        color: #fff;
        max-height: 32px;
    }

    .plugin-min-width {
        min-width: 1366px;
    }

    .table-header-tips-cls {
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
    }
</style>
