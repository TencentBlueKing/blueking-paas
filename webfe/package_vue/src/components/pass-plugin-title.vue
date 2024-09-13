<template>
  <div :class="['plugin-top-title', { 'no-shadow': !noShadow }]">
    <div class="title-container flex-row align-items-center">
      <i
        v-if="showBackIcon"
        class="paasng-icon paasng-arrows-left icon-cls-back mr5"
        @click="goBack"
      />
      <div class="title">
        {{ title }}
        <template v-if="versionData?.version">
          <div class="versionData-wrapper">
            <div class="detail-bar">
              <span class="left">{{ versionData?.version }}</span>
              <i class="line"></i>
              <span>{{ versionData?.source_version_name }}</span>
              <span
                class="commit-id"
                @click="toCodeRepository"
              >
                {{ versionData?.source_hash?.slice(-6) || '--' }}
              </span>
            </div>
          </div>
          <div class="status-wrapper">
            <round-loading v-if="!isCodecc && ['pending', 'initial'].includes(versionData.status)" />
            <div
              v-else
              :class="['dot', versionData[statusKey]]"
            />
            <span class="pl5">{{ $t(statusMap[versionData[statusKey]]) }}</span>
          </div>
        </template>
        <a
          v-if="isPluginDoc"
          target="_blank"
          :href="docUrl"
          class="plugin-doc"
        >
          <i class="paasng-icon paasng-question-circle" />
          {{ $t('插件文档') }}
        </a>
      </div>
      <span v-if="tips" class="tips">{{ tips }}</span>
    </div>
    <div class="right-tool flex-row align-items-center">
      <slot name="right"></slot>
    </div>
  </div>
</template>
<script>
import { bus } from '@/common/bus';

export default {
  props: {
    name: {
      type: String,
      default() {
        return '';
      },
    },
    versionData: {
      type: Object,
      default() {
        return {};
      },
    },
    noShadow: {
      type: Boolean,
      default: false,
    },
    isPluginDoc: {
      type: Boolean,
      default: false,
    },
    docUrl: {
      type: String,
      default: '',
    },
    tips: {
      type: String,
      default: '',
    },
    statusMap: {
      type: Object,
    },
    isCodecc: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      showBackIcon: false,
    };
  },
  computed: {
    statusKey() {
      return this.isCodecc ? 'display_status' : 'status';
    },
  },
  watch: {
    $route: {
      handler(value) {
        if (value) {
          this.title = this.name || (value.meta && value.meta.pathName);
          this.showBackIcon = value.meta && value.meta.supportBack;
        }
      },
      immediate: true,
    },
  },
  methods: {
    goBack() {
      const type = this.$route.query.type || 'prod';
      if (this.versionData?.version || type === 'test') {
        bus.$emit('stop-deploy', true);
        this.$router.push({
          name: 'pluginVersionManager',
          query: { type },
        });
      } else {
        this.$router.go(-1);
      }
    },
    toCodeRepository() {
      const location = this.versionData?.source_location;
      // 去除仓库.git后缀
      const url = `${location.replace(/\.git(?=\/|$)/, '')}/commit/${this.versionData?.source_hash}`;
      window.open(url, '_blank');
    },
  },
};
</script>
<style lang="scss" scoped>
.plugin-top-title {
  display: flex;
  justify-content: space-between;
  i {
    transform: translateY(0px);
  }
  .plugin-doc {
    position: absolute;
    right: 24px;
    font-size: 14px;
    i {
      transform: translateY(-1px);
    }
  }
  &.no-shadow {
    height: 52px;
    background: #fff;
    box-shadow: 0 3px 4px 0 #0000000a;
    position: relative;
    padding: 0 24px;
    .title-container .title {
      line-height: 52px;
    }
  }
  .title-container {
    flex: 1;
    .title {
      display: flex;
      align-items: center;
      font-size: 16px;
      color: #313238;
      letter-spacing: 0;
      line-height: 24px;
      .versionData-wrapper {
        margin-left: 16px;
        .detail-bar {
          display: flex;
          align-items: center;
          font-size: 12px;
          padding: 0 8px;
          height: 24px;
          background: #eaebf0;
          border-radius: 2px;
          color: #63656e;
          .left {
            font-weight: 700;
          }
          .line {
            display: inline-block;
            width: 1px;
            height: 16px;
            background: #dcdee5;
            margin: 0 8px;
          }
          .commit-id {
            color: #3a84ff;
            margin-left: 6px;
            cursor: pointer;
          }
        }
      }
      .status-wrapper {
        margin-left: 16px;
        font-size: 12px;
        color: #63656E;
        .bk-spin-loading {
          transform: translateY(-1px);
        }
      }
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 3px;
      }
      .successful,
      .fully_released {
        background: #e5f6ea;
        border: 1px solid #3fc06d;
      }
      .failed,
      .interrupted,
      .full_approval_failed,
      .gray_approval_failed {
        background: #ffe6e6;
        border: 1px solid #ea3636;
      }
      .full_approval_in_progress,
      .gray_approval_in_progress {
        background: #FFE8C3;
        border: 1px solid #FF9C01;
      }
      .in_gray {
        background: #E1ECFF;
        border: 1px solid #699DF4;
      }
      .rolled_back {
        background: #F0F1F5;
        border: 1px solid #DCDEE5;
      }
    }
    .icon-cls-back {
      color: #3a84ff;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
    .tips {
      margin-left: 16px;
      font-size: 12px;
      color: #979BA5;
    }
  }
}
</style>
