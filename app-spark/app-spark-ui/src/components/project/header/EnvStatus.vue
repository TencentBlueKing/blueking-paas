<template>
  <span class="env-status">
    <i class="env-status__dot" />
    沙箱环境 · 未发布
  </span>
</template>

<style lang="postcss" scoped>
.env-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  color: #2dcb56;
  font-size: 12px;
  background: rgba(45, 203, 86, 0.16);
  border-radius: 12px;
}

.env-status__dot {
  width: 6px;
  height: 6px;
  background: #2dcb56;
  border-radius: 50%;
}
</style>
