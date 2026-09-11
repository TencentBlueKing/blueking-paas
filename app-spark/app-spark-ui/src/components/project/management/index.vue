<template>
  <aside class="management-panel">
    <header class="management-panel__header">
      <div class="seg" role="tablist" aria-label="侧栏">
        <button
          type="button"
          role="tab"
          :class="{ 'is-on': activeTab === 'version' }"
          :aria-selected="activeTab === 'version'"
          @click="activeTab = 'version'"
        >
          版本
        </button>
        <button
          type="button"
          role="tab"
          :class="{ 'is-on': activeTab === 'data' }"
          :aria-selected="activeTab === 'data'"
          @click="activeTab = 'data'"
        >
          数据
        </button>
      </div>
    </header>
    <div class="management-panel__body">
      <VersionTimeline v-if="activeTab === 'version'" :versions="versions" />
      <DataPanel v-else />
    </div>
    <p class="management-panel__footer">
      回滚会同时回退页面与数据表结构，请确认后再操作。
    </p>
  </aside>
</template>

<script setup lang="ts">
// TODO: 待接入版本 API，当前为占位数据
import { ref } from 'vue';
import DataPanel from './DataPanel.vue';
import VersionTimeline from './VersionTimeline.vue';
import type { VersionItem } from './types.js';

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
  min-width: 240px;
  background: #fff;
  border-left: 1px solid var(--line, #e4e9f1);
}

.management-panel__header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  height: var(--rail-h, 56px);
  padding: 0 16px;
  border-bottom: 1px solid var(--line, #e4e9f1);
}

.seg {
  display: inline-flex;
  padding: 3px;
  background: #f3f4f7;
  border-radius: 10px;
}

.seg button {
  height: 28px;
  padding: 0 12px;
  color: var(--muted, #5c6573);
  font-size: 13px;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.seg button.is-on {
  color: var(--ink, #12141a);
  font-weight: 600;
  background: #fff;
  box-shadow: 0 1px 3px rgba(18, 28, 48, 0.08);
}

.seg button:focus-visible {
  outline: 2px solid var(--accent, #3d6dff);
  outline-offset: 2px;
}

.management-panel__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.management-panel__footer {
  padding: 12px 16px;
  color: var(--faint, #88919e);
  font-size: 12px;
  line-height: 1.6;
  border-top: 1px solid var(--line, #e4e9f1);
}
</style>
