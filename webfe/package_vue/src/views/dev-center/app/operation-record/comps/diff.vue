<template>
  <div :class="['record-diff-container', { 'full-screen': isFullscreen }]">
    <!-- top -->
    <div class="top-title">
      <div class="left item">
        <span>{{ $t('操作前') }}</span>
      </div>
      <div class="right item">
        <span>{{ $t('操作后') }}</span>
        <!-- 全屏 -->
        <i
          :title="isFullscreen ? $t('收起') : $t('展开')"
          :class="['paasng-icon', isFullscreen ? 'paasng-un-full-screen' : 'paasng-full-screen']"
          @click="toggleFullScreen"
        ></i>
      </div>
    </div>
    <code-diff
      ref="codeDiff"
      :old-content="oldCode"
      :new-content="newCode"
    />
    <section class="buttom-status-bar">
      <div
        class="item"
        v-for="item in statusMap"
        :key="item.name"
      >
        <div
          class="blocks"
          :style="{ background: item.color[0] }"
        ></div>
        <div
          class="blocks"
          :style="{ background: item.color[1], marginLeft: '1px' }"
        ></div>
        <span :style="{ color: item.color[2] }">{{ item.name }}</span>
      </div>
    </section>
  </div>
</template>

<script>
import codeDiff from './code-diff.vue';
export default {
  name: 'RecordDiff',
  components: {
    codeDiff,
  },
  props: {
    oldCode: {
      type: String,
      default: '',
    },
    newCode: {
      type: String,
      default: '',
    },
    language: {
      type: String,
      default: 'javascript',
    },
  },
  data() {
    return {
      statusMap: [
        {
          name: this.$t('删除'),
          color: ['#702622', '#666666', '#EA3636'],
        },
        {
          name: this.$t('变化'),
          color: ['#702622', '#3D4D1F', '#B6B6B6'],
        },
        {
          name: this.$t('新增'),
          color: ['#666666', '#3D4D1F', '#6E963C'],
        },
      ],
      isFullscreen: false,
    };
  },
  methods: {
    toggleFullScreen() {
      this.isFullscreen = !this.isFullscreen;
      this.$nextTick(() => {
        this.$refs.codeDiff?.layout();
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.record-diff-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1d1d1d;
  &.full-screen {
    position: fixed !important;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    height: 100vh;
    z-index: 9999;
  }
  .top-title {
    flex: 0 0 auto; /* 固定高度，不伸缩 */
    height: 44px;
    display: flex;
    align-items: center;
    .item {
      flex: 1;
      height: 100%;
      line-height: 44px;
      padding-left: 16px;
      background: #2e2e2e;
      &.right {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-left: 1px solid #313238;
        span {
          color: #3fc362;
          background: #144628;
        }
        i {
          margin-right: 24px;
          cursor: pointer;
          &:hover {
            color: #fff;
          }
        }
      }
      span {
        display: inline-block;
        height: 22px;
        line-height: 22px;
        padding: 0 8px;
        color: #64a0fa;
        background: #1e3567;
        border-radius: 2px;
      }
    }
  }
  .buttom-status-bar {
    position: relative;
    z-index: 99;
    flex: 0 0 auto; /* 固定高度，不伸缩 */
    display: flex;
    align-items: center;
    height: 48px;
    padding-left: 16px;
    background: #2e2e2e;
    box-shadow: 0 -1px 0 0 #313238;
    .item {
      display: flex;
      align-items: center;
      margin-right: 20px;
      .blocks {
        width: 12px;
        height: 12px;
      }
      span {
        font-size: 12px;
        margin-left: 6px;
      }
    }
  }
}
</style>
