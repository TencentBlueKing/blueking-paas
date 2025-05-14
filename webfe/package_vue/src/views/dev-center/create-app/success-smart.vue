<template lang="html">
  <div class="app-success-wrapper">
    <top-bar />
    <!-- smart 应用 -->
    <div class="container biz-create-success">
      <div class="success-wrapper">
        <div class="info">
          <p>
            <i class="paasng-icon paasng-check-1 text-success" />
          </p>
          <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
          <p>
            <bk-button
              :theme="'primary'"
              class="mr10"
              @click="handlePageJump(application?.type === 'default' ? 'appDeployForStag' : 'cloudAppDeployManageStag')"
            >
              {{ $t('部署应用') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handlePageJump(application?.type === 'default' ? 'appSummary' : 'cloudAppSummary')"
            >
              {{ $t('应用概览') }}
            </bk-button>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import topBar from './comps/top-bar.vue';
export default {
  components: {
    topBar,
  },
  data() {
    const appCode = this.$route.params.id;
    return {
      appCode,
      application: {},
    };
  },
  created() {
    const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
    this.$http.get(url).then((response) => {
      const body = response;
      this.application = body.application;
    });
  },
  methods: {
    handlePageJump(name) {
      this.$router.push({
        name,
        params: {
          id: this.appCode,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.app-success-wrapper {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  background: #f5f7fa;

  .biz-create-success {
    background: #f5f7fa;
    padding-bottom: 20px;
    padding-top: calc(var(--app-notice-height) + 74px);
  }
  .success-wrapper {
    .info {
      background: #ffffff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }
  }
}
.success-wrapper {
  width: 100%;
  border-radius: 2px;
  .info {
    padding-top: 45px;
    padding-bottom: 40px;
    p:nth-child(1) {
      margin: 0 auto;
      width: 84px;
      height: 84px;
      border-radius: 50%;
      text-align: center;
      background: #e5f6ea;
      .text-success {
        font-weight: bold;
        line-height: 84px;
        transform: scale(2);
        font-size: 20px;
        color: #3fc06d;
      }
    }
    p:nth-child(2) {
      margin-top: 16px;
      font-size: 16px;
      font-weight: bold;
      color: #313238;
      text-align: center;
    }
    p:nth-child(3) {
      margin-top: 12px;
      font-size: 14px;
      color: #63656e;
      text-align: center;
      .link {
        color: #3a84ff;
        cursor: pointer;
        &:hover {
          color: #699df4;
        }
      }
    }
  }
}
</style>
