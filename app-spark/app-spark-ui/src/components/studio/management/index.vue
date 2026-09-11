<template>
  <aside class="management-panel">
    <bk-tab v-model:active="activeTab" type="unborder-card" class="management-panel__tabs">
      <bk-tab-panel name="version" label="版本">
        <VersionTimeline :versions="versions" />
      </bk-tab-panel>
      <bk-tab-panel name="data" label="数据">
        <DataPanel />
      </bk-tab-panel>
    </bk-tab>
    <p class="management-panel__footer">
      回滚会同时回退页面与数据表结构，请确认后再操作。
    </p>
  </aside>
</template>

<script setup lang="ts">
// TODO: Studio 占位版本列表，待接入真实版本 API
import { ref } from 'vue';
import DataPanel from './DataPanel.vue';
import VersionTimeline from './VersionTimeline.vue';
import type { VersionItem } from './types';

const activeTab = ref('version');

const versions: VersionItem[] = [
  {
    id: 'v5',
    title: '改按钮：红橙渐变 + 立即预约',
    time: '3分钟前',
    current: true,
  },
  {
    id: 'v4',
    title: '调整模块节奏：突出预约区',
    time: '18分钟前',
  },
  {
    id: 'v3',
    title: '按海报提取配色并应用到首屏',
    time: '36分钟前',
  },
  {
    id: 'v2',
    title: '生成活动页骨架 + 数据表',
    time: '1小时前',
    tag: '全量生成',
  },
  {
    id: 'v1',
    title: '创建应用 新品预约活动页',
    time: '今天 14:02',
  },
];
</script>

<style lang="postcss" scoped>
.management-panel {
  display: flex;
  flex-direction: column;
  width: 300px;
  min-width: 260px;
  background: #fff;
  border-left: 1px solid #dcdee5;
}

.management-panel__tabs {
  flex: 1;
  min-height: 0;
}

.management-panel__footer {
  padding: 12px 16px;
  color: #979ba5;
  font-size: 12px;
  line-height: 1.6;
  border-top: 1px solid #dcdee5;
}

:deep(.bk-tab-header) {
  padding: 0 12px;
}

:deep(.bk-tab-content) {
  height: calc(100% - 42px);
  padding: 0;
  overflow: auto;
}
</style>
