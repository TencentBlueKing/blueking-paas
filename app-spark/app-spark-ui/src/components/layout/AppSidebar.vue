<template>
  <nav
    :class="['app-sidebar', { 'is-collapsed': collapsed }]"
    aria-label="主导航"
  >
    <router-link
      class="app-sidebar__item"
      :to="{ name: 'home' }"
      :title="collapsed ? '首页' : undefined"
    >
      <AppIcon name="home" />
      <span class="app-sidebar__label">首页</span>
    </router-link>
    <router-link
      class="app-sidebar__item"
      :to="{ name: 'projects' }"
      :title="collapsed ? '项目列表' : undefined"
    >
      <AppIcon name="list" />
      <span class="app-sidebar__label">项目列表</span>
    </router-link>
    <button
      type="button"
      class="app-sidebar__toggle"
      :aria-expanded="!collapsed"
      :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
      :title="collapsed ? '展开' : undefined"
      @click="toggle"
    >
      <AppIcon :name="collapsed ? 'panel-left-open' : 'panel-left-close'" />
      <span class="app-sidebar__label">{{ collapsed ? '展开' : '收起' }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from '@/components/AppIcon.vue';

const STORAGE_KEY = 'app-spark:sidebar';
const collapsed = ref(false);

try {
  collapsed.value = localStorage.getItem(STORAGE_KEY) === 'collapsed';
} catch {
  collapsed.value = false;
}

const toggle = () => {
  collapsed.value = !collapsed.value;
  try {
    localStorage.setItem(STORAGE_KEY, collapsed.value ? 'collapsed' : 'expanded');
  } catch {
    // 存储不可用时只保留当前页状态。
  }
};
</script>

<style lang="postcss" scoped>
.app-sidebar {
  display: flex;
  flex: 0 0 var(--sidebar-w);
  flex-direction: column;
  gap: 4px;
  width: var(--sidebar-w);
  padding: 16px 12px;
  overflow: hidden;
  background: #fff;
  border-right: 1px solid var(--line);
}

.app-sidebar.is-collapsed {
  flex-basis: var(--sidebar-collapsed-w);
  width: var(--sidebar-collapsed-w);
}

.app-sidebar__item,
.app-sidebar__toggle {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 40px;
  padding: 0 11px;
  overflow: hidden;
  color: var(--muted);
  font-size: 14px;
  text-decoration: none;
  white-space: nowrap;
  background: transparent;
  border: 0;
  border-radius: 10px;
  cursor: pointer;
  transition: color 120ms ease, background-color 120ms ease;
}

.app-sidebar__item :deep(.app-icon),
.app-sidebar__toggle :deep(.app-icon) {
  flex: 0 0 18px;
  width: 18px;
  height: 18px;
}

.app-sidebar__label {
  overflow: hidden;
  opacity: 1;
  transition: opacity 160ms ease;
}

.app-sidebar.is-collapsed .app-sidebar__item,
.app-sidebar.is-collapsed .app-sidebar__toggle {
  gap: 0;
}

.app-sidebar.is-collapsed .app-sidebar__label {
  width: 0;
  opacity: 0;
}

.app-sidebar__item:hover,
.app-sidebar__toggle:hover {
  color: var(--ink);
  background: var(--subtle-bg);
}

.app-sidebar__item.router-link-exact-active {
  color: var(--accent);
  font-weight: 600;
  background: var(--accent-soft);
}

.app-sidebar__toggle {
  margin-top: auto;
  color: var(--faint);
  font-size: 13px;
}

.app-sidebar__item:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: 2px;
}

.app-sidebar__toggle:focus-visible {
  outline: none;
}

@media (max-width: 760px) {
  .app-sidebar {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-sidebar__item,
  .app-sidebar__toggle,
  .app-sidebar__label {
    transition: none;
  }
}
</style>
