<template>
  <div class="container">
    <div class="create-item">
      <div class="item-title">
        {{ $t('代码来源') }}
      </div>
      <div
        id="choose-cluster"
        class="form-group-dir"
      >
        <!-- 骨架屏 -->
        <content-loader
          v-if="isContentLoading"
          :height="30"
          :speed="2"
          preserveAspectRatio="none"
          :primaryColor="loadingConf.primaryColor"
          :secondaryColor="loadingConf.secondaryColor"
        >
          <rect
            x="0"
            y="5"
            width="calc(25% - 8px)"
            height="20"
          />
          <rect
            x="25%"
            y="5"
            width="calc(25% - 8px)"
            height="20"
          />
          <rect
            x="50%"
            y="5"
            width="calc(25% - 8px)"
            height="20"
          />
          <rect
            x="75%"
            y="5"
            width="calc(25% - 8px)"
            height="20"
          />
        </content-loader>
        <ul
          class="tab-box mt10"
          v-else
        >
          <li
            v-for="app in visibleAppTypes"
            :key="app.type"
            :class="['tab-item', { active: appType === app.type }]"
            @click="handleToggleType(app.type)"
          >
            {{ app.title }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import { ContentLoader } from 'vue-content-loader';
import { mapState } from 'vuex';

export default {
  components: {
    ContentLoader,
  },
  data() {
    return {
      appType: 'default',
      isContentLoading: true,
    };
  },
  computed: {
    ...mapState(['userFeature', 'platformFeature', 'loadingConf', 'isPlatformFeatureLoading']),
    visibleAppTypes() {
      // 静态项（始终显示）
      const staticApps = [
        { title: this.$t('代码仓库'), type: 'default', isShow: true },
        { title: this.$t('镜像仓库'), type: 'image', isShow: true },
      ];
      // 动态项（依赖 Vuex 状态）
      const dynamicApps = [
        {
          title: this.$t('蓝鲸运维开发平台'),
          type: 'bkLesscode',
          isShow: this.platformFeature.BK_LESSCODE_APP || false,
        },
        {
          title: this.$t('S-mart 应用'),
          type: 'smart',
          isShow: this.userFeature.ALLOW_CREATE_SMART_APP || false,
        },
      ];
      return [...staticApps, ...dynamicApps].filter((app) => app.isShow);
    },
  },
  watch: {
    platformFeature: {
      handler(newVal, oldVal) {
        if (Object.keys(newVal)?.length && oldVal === undefined) {
          this.isContentLoading = false;
          return;
        }
        setTimeout(() => {
          this.isContentLoading = false;
        }, 500);
      },
      deep: true,
      immediate: true,
    },
  },
  methods: {
    handleToggleType(type) {
      this.$emit('on-change-type', type);
      this.appType = type;
    },
  },
};
</script>

<style lang="scss" scoped>
@import './default.scss';
@import '~@/assets/css/mixins/border-active-logo.scss';
.container {
  width: 1200px;
  margin: auto;
  .create-item {
    width: 100%;
    .form-group-dir {
      display: block;
    }
  }
}
.tab-box {
  margin: auto;
  height: 56px;
  list-style: none;
  display: flex;

  .tab-item {
    flex: 1;
    margin-right: 16px;
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
</style>
