<template>
  <!-- TODO: Studio 占位面包屑，待接入真实项目名 -->
  <bk-breadcrumb class="app-breadcrumb" separator="/">
    <bk-breadcrumb-item :to="{ name: 'home' }">我的应用</bk-breadcrumb-item>
    <bk-breadcrumb-item>新品预约活动页</bk-breadcrumb-item>
  </bk-breadcrumb>
</template>

<style lang="postcss" scoped>
.app-breadcrumb {
  :deep(.bk-breadcrumb-item) {
    color: #c4c6cc;
  }

  :deep(.bk-breadcrumb-item:last-child) {
    color: #fff;
  }

  :deep(.bk-breadcrumb-separator) {
    color: #979ba5;
  }
}
</style>
