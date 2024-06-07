<template>
  <div class="render-member-list-wrapper">
    <div class="content">
      <div
        v-for="(item, index) in data"
        :key="index"
        class="member-item"
        :title="item.name"
      >
        <span class="left-icon">
          <i
            v-if="type === 'user'"
            class="paasng-icon icon paasng-user-shape"
          />
          <img
            v-else
            class="folder-icon"
            src="/static/images/file-close.svg"
            alt=""
          />
        </span>
        <span class="member-name">
          {{ item.name }}
        </span>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  name: 'RenderMemberList',
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    type: {
      type: String,
      default: 'user',
    },
  },
};
</script>
<style lang="scss" scoped>
.render-member-list-wrapper {
  color: #63656e;
  .content {
    .icon {
      font-size: 16px;
      display: inline-block;
      color: #a3c5fd;
      vertical-align: middle;
    }
    .member-name {
      margin-left: 10px;
      font-size: 14px;
      display: inline-block;
      vertical-align: middle;
    }
    .folder-icon {
      width: 16px;
      vertical-align: middle;
    }
    .member-item {
      height: 36px;
      line-height: 36px;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;

      .left-icon {
        display: inline-block;
        width: 18px;
      }
    }
  }
}
</style>
