<template>
  <header class="app-header">
    <router-link
      class="app-header__brand"
      :to="{ name: 'home' }"
      aria-label="返回 App-Spark 首页"
    >
      <span class="brand-mark" aria-hidden="true">
        <i class="brand-mark__spark" />
        <i class="brand-mark__spark is-small" />
      </span>
      <span class="app-header__name">App-<em>Spark</em></span>
    </router-link>
    <div class="app-header__actions">
      <UserInfo />
    </div>
  </header>
</template>

<script setup lang="ts">
import UserInfo from '@/components/user-info.vue';
</script>

<style lang="postcss" scoped>
.app-header {
  display: flex;
  flex: 0 0 var(--nav-h);
  align-items: center;
  justify-content: space-between;
  height: var(--nav-h);
  padding-right: 24px;
  overflow: hidden;
  background: var(--nav-bg);
}

.app-header__brand {
  display: flex;
  flex: 0 0 var(--sidebar-w);
  align-items: center;
  align-self: stretch;
  padding: 0 16px;
  color: #fff;
  text-decoration: none;
}

.brand-mark {
  position: relative;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  overflow: hidden;
  background: var(--brand-gradient);
  border-radius: 9px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14), 0 4px 14px var(--brand-glow);
  transition: box-shadow 240ms ease;
}

.brand-mark::after {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 25% 20%, rgba(255, 255, 255, 0.35), transparent 55%);
  content: "";
}

.brand-mark__spark {
  position: absolute;
  top: 7px;
  left: 7px;
  z-index: 1;
  width: 16px;
  height: 16px;
  background: #fff;
  clip-path: var(--spark-shape);
  filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.8));
  transition: transform 400ms cubic-bezier(0.16, 1, 0.3, 1);
}

.brand-mark__spark.is-small {
  top: 4px;
  left: 19px;
  width: 7px;
  height: 7px;
  animation: spark-twinkle 2.8s ease-in-out infinite;
}

.app-header__brand:hover .brand-mark {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.2), 0 4px 20px var(--brand-glow-strong);
}

.app-header__brand:hover .brand-mark__spark:not(.is-small) {
  transform: rotate(180deg) scale(1.1);
}

.app-header__brand:focus-visible {
  outline: 2px solid #8aa8ff;
  outline-offset: -2px;
}

.app-header__name {
  margin-left: 12px;
  overflow: hidden;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  line-height: 24px;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.app-header__name em {
  color: #9db4ff;
  font-style: normal;
}

.app-header__actions {
  display: flex;
  align-items: center;
  min-width: 0;
}

.app-header__actions :deep(.user-name) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--nav-text);
}

.app-header__actions :deep(.user-name:hover),
.app-header__actions :deep(.user-name:focus-visible) {
  color: #fff;
}

@keyframes spark-twinkle {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.6);
  }

  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .brand-mark__spark {
    animation: none;
    transition: none;
  }
}

@media (max-width: 760px) {
  .app-header {
    padding-right: 12px;
  }

  .app-header__brand {
    flex-basis: auto;
    padding-right: 12px;
  }

  .app-header__name {
    margin-left: 9px;
  }
}
</style>
