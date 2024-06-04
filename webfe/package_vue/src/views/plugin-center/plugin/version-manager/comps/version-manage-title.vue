<template>
  <div class="version-manage-title no-shadow">
    <div class="title-container flex-row align-items-center">
      <div class="title">
        {{ title }}
      </div>
      <section
        class="publish-switch-wrapper"
        v-if="isShowTab"
      >
        <div
          v-for="(item, index) in tabList"
          :class="['tab-item', { active: type === item.key }]"
          :key="index"
          @click="handleTabClick(item)"
        >
          {{ $t(item.title) }}
        </div>
      </section>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    name: {
      type: String,
      default() {
        return '';
      },
    },
    type: {
      type: String,
      default: 'test',
    },
    isShowTab: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      tabList: [
        { title: '测试记录', key: 'test' },
        { title: '版本发布', key: 'prod' },
      ],
    };
  },
  watch: {
    $route: {
      handler(value) {
        if (value) {
          this.title = this.name || (value.meta && value.meta.pathName);
        }
      },
      immediate: true,
    },
  },
  methods: {
    handleTabClick(data) {
      this.$emit('change-type', data.key);
    },
  },
};
</script>
<style lang="scss" scoped>
.version-manage-title {
  i {
    transform: translateY(0px);
  }
  &.no-shadow {
    height: 52px;
    background: #fff;
    box-shadow: 0 3px 4px 0 #0000000a;
    position: relative;
    padding: 0 24px;
    .title-container .title {
      line-height: 52px;
    }
  }
  .title-container {
    position: relative;
    justify-content: center;
    .title {
      position: absolute;
      left: 0;
      top: 0;
      font-size: 16px;
      color: #313238;
      letter-spacing: 0;
    }
    .icon-cls-back {
      color: #3a84ff;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
  }
  .publish-switch-wrapper {
    height: 52px;
    flex: 1;
    display: flex;
    justify-content: center;
    align-content: center;
    .tab-item {
      position: relative;
      padding: 0 24px;
      line-height: 52px;
      font-size: 14px;
      color: #63656E;

      &:hover {
        cursor: pointer;
      }

      &.active {
        color: #3a84ff;
        background: #f0f5ff;
        &::before {
          content: '';
          position: absolute;
          width: 100%;
          top: 0;
          left: 0;
          height: 1px;
          background: #3a84ff;
        }
      }
    }
  }
}
</style>
