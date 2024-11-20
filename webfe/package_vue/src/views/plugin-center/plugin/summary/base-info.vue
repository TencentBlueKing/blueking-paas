<template>
  <div class="plugin-home-base-info">
    <div class="title">{{ $t('基本信息') }}</div>
    <div class="base-info">
      <p
        v-bk-overflow-tips
        class="item"
      >
        <span class="lable">{{ $t('插件类型：') }}</span>
        <span
          class="content"
          v-bk-overflow-tips
        >
          {{ data.pd_name ?? '--' }}
        </span>
      </p>
      <p
        v-bk-overflow-tips
        class="item"
      >
        <span class="lable">{{ $t('开发语言：') }}</span>
        <span class="content">{{ data.language ?? '--' }}</span>
      </p>
      <p class="item repos">
        <span class="lable">{{ $t('代码仓库：') }}</span>
        <span class="links">
          <span
            class="content"
            v-bk-overflow-tips
          >
            {{ data.repository }}
          </span>
          <a
            :href="data.repository"
            target="_blank"
            style="color: #979ba5"
          >
            <i class="paasng-icon paasng-jump-link icon-cls-link mr5 copy-text" />
          </a>
        </span>
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'PluginRightInfo',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
};
</script>

<style lang="scss" scoped>
.plugin-home-base-info {
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    margin-bottom: 8px;
  }
  .base-info {
    .item {
      display: flex;
      align-items: center;
      line-height: 32px;
      .lable {
        flex-shrink: 0;
        color: #4d4f56;
      }
      .content {
        flex: 1;
        color: #313238;
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
      }
    }
    .repos {
      .links {
        display: flex;
        overflow: hidden;
      }
      .copy-text {
        color: #3a84ff;
        cursor: pointer;
      }
    }
  }
}
</style>
