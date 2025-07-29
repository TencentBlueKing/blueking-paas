<template>
  <div class="home-main-content">
    <section
      class="home-record-tab-cls"
      v-show="showPanels.length"
    >
      <div class="tab-header">
        <div
          v-for="(panel, index) in showPanels"
          :key="index"
          :class="['tab-item', { active: panel.name === active }]"
          @click="handleTabClick(panel)"
        >
          {{ panel.label }}
        </div>
      </div>
      <div
        ref="tabContent"
        class="tab-content"
      >
        <!--应用闲置看板功能 -->
        <idle-app-dashboard
          v-show="active === 'idle'"
          @async-list-length="handlePanelUpdate"
        />
        <!-- 告警记录 -->
        <template v-if="platformFeature.MONITORING">
          <alarm-records
            v-show="active === 'alarm'"
            @async-list-length="handlePanelUpdate"
          />
        </template>
      </div>
    </section>
    <div
      class="no-data card-style"
      v-show="!showPanels.length"
    >
      <!-- 空状态 -->
      <img src="/static/images/home-empty-state.png" />
      <p class="empty-text">{{ $t('太棒了！') }}</p>
      <p
        class="empty-tips"
        v-dompurify-html="emptyTips"
      ></p>
    </div>
    <!-- 操作记录 -->
    <section class="operation-records">
      <recent-operation-records :content-height="contentHeight" />
    </section>
  </div>
</template>

<script>
import idleAppDashboard from './idle-app-dashboard.vue';
import alarmRecords from './alarm-records.vue';
import recentOperationRecords from './recent-operation-records.vue';
export default {
  name: 'HomeTab',
  components: {
    idleAppDashboard,
    alarmRecords,
    recentOperationRecords,
  },
  data() {
    return {
      active: 'idle',
      // 初始无数据，防止网络延迟出现的tab延时情况
      panels: [],
      contentHeight: 0,
      resizeObserver: null,
    };
  },
  computed: {
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    showPanels() {
      if (this.platformFeature.MONITORING) {
        return this.panels;
      }
      return this.panels.filter((item) => item.name !== 'alarm');
    },
    appChartInfo() {
      return this.$store.state.baseInfo.appChartData;
    },
    emptyTips() {
      return this.$t('您当前共管理 <i>{n}</i> 个应用，无任何应用处于告警或闲置状态，请继续保持！', {
        n: this.appChartInfo?.allCount,
      });
    },
  },
  watch: {
    showPanels(newPanels) {
      if (newPanels.length) {
        this.handleTabClick(newPanels[0]);
      }
    },
  },
  mounted() {
    this.updateContainerHeight();

    // 创建一个 ResizeObserver 实例
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const newHeight = entry.contentRect.height;

        // 如果高度发生变化
        if (newHeight !== this.contentHeight - 32) {
          window.requestAnimationFrame(() => {
            this.contentHeight = newHeight + 32;
          });
        }
      }
    });
    this.resizeObserver.observe(this.$refs.tabContent);
  },
  beforeDestroy() {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  },
  methods: {
    handleTabClick(data) {
      this.active = data.name;
      this.$nextTick(() => {
        this.updateContainerHeight();
      });
    },
    // 根据操作手动更新
    updateContainerHeight() {
      this.contentHeight = this.$refs.tabContent?.offsetHeight;
    },
    handlePanelUpdate(data) {
      const { name, length } = data;
      if (length === 0) {
        if (!this.panels.length) return;
        // 移除对应的 tab 项
        this.panels = this.panels.filter((panel) => panel.name !== name);
        this.active = this.panels[0]?.name;
      } else {
        // 确保在 length > 0 时，该 tab 存在于 panels 中
        if (!this.panels.some((panel) => panel.name === name)) {
          this.isLoading = true;
          if (name === 'idle') {
            this.panels.unshift({ name: 'idle', label: this.$t('闲置应用') });
          } else if (name === 'alarm') {
            this.panels.push({ name: 'alarm', label: this.$t('告警记录') });
          }
        }
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.home-main-content {
  margin-top: 24px;
  display: flex;
  min-width: auto;
  .home-record-tab-cls {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 604px;
  }
  .no-data {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 604px;
    background: #fff;
    color: #63656e;
    img {
      width: 300px;
      height: 150px;
    }
    .empty-text {
      font-size: 16px;
    }
    .empty-text,
    .empty-tips {
      margin-top: 8px;
    }
  }
  .operation-records {
    width: 320px;
    margin-left: 24px;
    flex-shrink: 0;
  }
}

.home-record-tab-cls {
  .tab-header {
    display: flex;
    align-items: center;
  }
  .tab-content {
    min-height: 562px;
    padding: 16px;
    box-shadow: 0 2px 4px 0 #1919290d;
    border-radius: 2px;
    background: #fff;
  }
  .tab-item {
    position: relative;
    height: 42px;
    padding: 0 24px;
    line-height: 42px;
    font-size: 14px;
    color: #63656e;
    cursor: pointer;
    background: #eaebf0;
    border-radius: 4px 4px 0 0;
    &.active {
      background: #fff;
      color: #3a84ff;
    }
    &:first-child {
      margin-right: 8px;
    }
  }
}
/deep/ .no-data .empty-tips i {
  font-style: normal;
  font-weight: 700;
  color: #3a84ff;
}
</style>
