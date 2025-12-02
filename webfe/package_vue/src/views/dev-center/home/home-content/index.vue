<template>
  <div class="home-main-content">
    <section class="home-record-tab-cls">
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
        <IdleAppDashboard
          v-if="platformFeature.MONITORING"
          v-show="active === 'idle'"
          @async-list-length="handlePanelUpdate"
        />
        <!-- 告警记录 -->
        <AlarmRecords
          v-if="platformFeature.MONITORING"
          v-show="active === 'alarm'"
          @async-list-length="handlePanelUpdate"
        />
        <!-- 我收藏的应用 -->
        <MarkedApps
          v-show="active === 'marked'"
          @async-list-length="handlePanelUpdate"
        />
      </div>
    </section>
    <!-- 操作记录 -->
    <section class="operation-records">
      <RecentOperationRecords :content-height="contentHeight" />
    </section>
  </div>
</template>

<script>
import IdleAppDashboard from './idle-app-dashboard.vue';
import AlarmRecords from './alarm-records.vue';
import RecentOperationRecords from './recent-operation-records.vue';
import MarkedApps from './marked-apps.vue';
export default {
  name: 'HomeTab',
  components: {
    IdleAppDashboard,
    AlarmRecords,
    RecentOperationRecords,
    MarkedApps,
  },
  data() {
    return {
      active: '',
      panelShowStates: {
        idle: false,
        alarm: false,
        marked: true, // 收藏应用始终显示
      },
      contentHeight: 0,
      resizeObserver: null,
      userHasManuallySelected: false, // 标记用户是否手动选择过tab
    };
  },
  computed: {
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    allPanels() {
      return [
        {
          name: 'idle',
          label: this.$t('闲置应用'),
        },
        {
          name: 'alarm',
          label: this.$t('告警记录'),
        },
        {
          name: 'marked',
          label: this.$t('我收藏的应用'),
        },
      ];
    },
    // 根据平台功能过滤后的面板
    availablePanels() {
      return this.allPanels.filter((panel) => {
        const isMonitoringRelatedPanel = panel.name === 'idle' || panel.name === 'alarm';
        if (panel.name === 'marked') {
          return true;
        }
        // 监控功能关闭时，不显示闲置应用和告警记录
        if (!this.platformFeature.MONITORING && isMonitoringRelatedPanel) {
          return false;
        }
        return true;
      });
    },
    showPanels() {
      return this.availablePanels.filter((panel) => {
        return this.panelShowStates[panel.name];
      });
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
    showPanels: {
      handler(newPanels) {
        if (newPanels.length > 0) {
          const currentActiveExists = this.active && newPanels.some((p) => p.name === this.active);
          // 如果没有激活项，或当前激活项不存在，或用户还未手动选择过，则自动选择第一个
          if (!currentActiveExists || !this.userHasManuallySelected) {
            this.active = newPanels[0].name;
          }
        }
      },
      immediate: true,
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
      this.userHasManuallySelected = true; // 标记用户已手动选择
      this.$nextTick(() => {
        this.updateContainerHeight();
      });
    },
    // 根据操作手动更新
    updateContainerHeight() {
      this.contentHeight = this.$refs.tabContent?.offsetHeight;
    },
    // 设置默认激活的面板
    setDefaultActivePanel() {
      if (this.showPanels.length > 0) {
        const currentActiveExists = this.active && this.showPanels.some((panel) => panel.name === this.active);
        if (!currentActiveExists) {
          this.active = this.showPanels[0].name;
        }
      }
    },
    handlePanelUpdate({ name, length }) {
      this.$set(this.panelShowStates, name, length > 0);
      this.$nextTick(() => {
        this.setDefaultActivePanel();
      });
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
    gap: 8px;
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
  }
}
/deep/ .no-data .empty-tips i {
  font-style: normal;
  font-weight: 700;
  color: #3a84ff;
}
</style>
