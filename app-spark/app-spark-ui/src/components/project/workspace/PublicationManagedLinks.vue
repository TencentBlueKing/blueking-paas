<template>
  <div v-if="links" class="publication-managed">
    <p>项目由 <strong>蓝鲸开发者中心</strong> 托管，更多操作：</p>
    <ul>
      <li v-for="item in items" :key="item.key">
        <a :href="item.url" target="_blank" rel="noopener noreferrer">
          <span class="publication-managed__label">{{ item.label }}</span>
          <span class="publication-managed__desc">{{ item.description }}</span>
          <AppIcon name="external-link" />
        </a>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import AppIcon from '@/components/AppIcon.vue';
import type { PublicationDevCenterLinks } from '@/http/types';

const props = defineProps<{ links: PublicationDevCenterLinks | null }>();

const items = computed(() => {
  const links = props.links;
  if (!links) return [];
  return [
    { key: 'logs', label: '日志查询', description: '查看项目访问日志', url: links.logs },
    { key: 'deployments', label: '部署管理', description: '查看已部署实例与历史', url: links.deployments },
    { key: 'env-vars', label: '环境变量', description: '查看和管理环境变量', url: links.env_vars },
    { key: 'members', label: '成员管理', description: '管理项目权限', url: links.members },
  ];
});
</script>

<style lang="postcss" scoped>
.publication-managed {
  padding: 10px 12px 6px;
  background: var(--subtle-bg);
  border-radius: 10px;
}

.publication-managed p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}

.publication-managed strong {
  color: var(--ink);
  font-weight: 600;
}

.publication-managed ul {
  margin: 4px -6px 0;
  padding: 0;
  list-style: none;
}

.publication-managed a {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  font-size: 12px;
  text-decoration: none;
  border-radius: 6px;
}

.publication-managed a:hover {
  background: var(--hover-bg);
}

.publication-managed a:focus-visible {
  outline: 2px solid var(--accent-focus);
  outline-offset: -2px;
}

.publication-managed__label {
  flex-shrink: 0;
  color: var(--accent);
  font-weight: 500;
}

.publication-managed__desc {
  flex: 1;
  min-width: 0;
  color: var(--faint);
}

.publication-managed .app-icon {
  color: var(--faint);
  font-size: 12px;
}
</style>
