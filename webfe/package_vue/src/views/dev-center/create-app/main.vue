<template lang="html">
  <div
    class="paas-content pb-24"
    data-test-id="create_content_App"
  >
    <div class="big-title">
      <span>{{ $t('创建应用') }}</span>
    </div>
    <div class="tab-box">
      <li
        :class="['tab-item', { active: appType === 'cloud' }]"
        @click="handleToggleType('cloud')"
      >
        {{ $t('云原生应用') }}
      </li>
      <li
        :class="['tab-item', { active: appType === 'external' }]"
        @click="handleToggleType('external')"
      >
        {{ $t('外链应用') }}
      </li>
    </div>
    <create-cloud-app
      v-if="appType === 'cloud'"
      key="cloud"
      ref="cloud"
    />
    <create-external-app
      v-else-if="appType === 'external'"
      key="external"
      ref="external"
    />
  </div>
</template>

<script>
import createExternalApp from './external';
import createCloudApp from './cloud';

const queryMap = {
  default: 'app',
  cloud: 'cloudNativeApp',
  smart: 'smartApp',
  external: 'externalApp',
};

export default {
  components: {
    createExternalApp,
    createCloudApp,
  },
  data() {
    return {
      appType: 'cloud',
    };
  },
  computed: {
    searchQuery() {
      return this.$route.query;
    },
  },
  created() {
    this.switchAppType();
  },
  methods: {
    async handleToggleType(type) {
      // 内容变更弹窗提示
      const isSwitching = await this.$refs[this.appType]?.handleBeforeFunction();
      // 存在undefined情况，直接判断是否为false
      if (isSwitching === false) {
        return;
      }
      if (this.searchQuery.type) {
        const query = JSON.parse(JSON.stringify(this.searchQuery));
        query.type = queryMap[type];
        this.$router.push({ path: this.$route.path, query });
      }
      if (this.appType === type) {
        return false;
      }
      this.appType = type;
    },
    switchAppType() {
      if (this.searchQuery.type) {
        switch (this.searchQuery.type) {
          case 'cloudNativeApp':
            this.appType = 'cloud';
            break;
          case 'smartApp':
            this.appType = 'smart';
            break;
          case 'externalApp':
            this.appType = 'external';
            break;
          default:
            this.appType = 'default';
            break;
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/border-active-logo.scss';
.tab-box {
  width: 1200px;
  margin: auto;
  height: 56px;
  margin-top: 16px;
  list-style: none;
  display: flex;
  justify-content: space-between;

  .tab-item {
    flex: 1;
    margin-right: 24px;
    height: 56px;
    line-height: 56px;
    text-align: center;
    background: #f0f1f5;
    border-radius: 2px;
    font-size: 14px;
    color: #63656e;
    cursor: pointer;
    position: relative;

    &:last-of-type {
      margin-right: 0 !important;
    }

    &.active {
      background: #fff;
      border: 2px solid #3a84ff;
      color: #3a84ff;

      @include border-active-logo;
    }
  }
}

.big-title {
  position: relative;
  position: relative;
  height: 52px;
  line-height: 52px;
  text-align: center;
  font-size: 16px;
  color: #313238;
  background: #ffffff;
  box-shadow: 0 1px 0 0 #dcdee5, 0 3px 4px 0 #4070cb0f;

  & span {
    display: inline-block;
    padding: 0 24px;
    background: #fff;
    line-height: 34px;
    font-size: 18px;
    color: #333;
    z-index: 9;
  }
}
</style>
