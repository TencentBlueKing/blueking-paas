<template>
  <div class="service-list">
    <section
      class="custom-service-loader"
      v-if="loading"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="loader-item"
      ></div>
    </section>
    <div
      v-else
      v-for="item in services"
      :key="item.id"
      class="list-item"
      :class="{ active: selectedItem === item.uuid, 'not-visible': !item.is_visible }"
      @click="handleSelected(item)"
    >
      <!-- 左侧图标区域 -->
      <div class="logo-wrapper">
        <img
          class="logo"
          :src="item.logo"
        />
      </div>
      <!-- 中间内容区域 -->
      <div class="content">
        <div class="title">
          {{ item.display_name }}
          <span class="short-name">({{ item.name }})</span>
        </div>
        <!-- tag -->
        <div class="tag-list">
          <span
            class="tag"
            v-if="item.category_id === 1"
          >
            {{ $t('数据存储') }}
          </span>
          <span
            class="tag"
            v-else-if="item.category_id === 2"
          >
            {{ $t('监控检测') }}
          </span>
          <span
            class="tag"
            v-if="item.origin"
          >
            {{ item.origin === 'local' ? $t('本地增强服务') : $t('远程增强服务') }}
          </span>
          <span class="tag">
            {{ item.is_visible ? $t('可见') : $t('不可见') }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    loading: {
      type: Boolean,
      default: false,
    },
    services: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      selectedItem: '', // 当前选中项
    };
  },
  methods: {
    handleSelected(item) {
      if (this.selectedItem === item.uuid) return;
      this.selectedItem = item.uuid;
      this.$emit('change', item);
    },
  },
};
</script>

<style lang="scss" scoped>
.service-list {
  padding: 12px;
  flex-shrink: 0;
  width: 280px;
  .custom-service-loader {
    .loader-item {
      height: 56px;
      margin-bottom: 8px;
      background-color: #fff;
    }
  }

  .list-item {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 56px;
    padding: 8px;
    margin-bottom: 8px;
    background: #fff;
    box-shadow: 0 1px 3px 0 #0000001a;
    border-radius: 4px;
    cursor: pointer;
    &.active {
      border: 1px solid #3a84ff;
      background: #f0f5ff;
      .tag-list {
        opacity: 1 !important;
        .tag {
          background: #fff;
        }
      }
      .logo-wrapper {
        background: #fff;
      }
    }
    &.not-visible {
      .title {
        color: #979ba5;
        .short-name {
          color: #dcdee5;
        }
      }
      .tag-list {
        opacity: 0.5;
      }
    }
    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .logo-wrapper {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: #f5f7fa;
      border-radius: 2px;
      .logo {
        width: 24px;
        height: 24px;
        display: block;
      }
    }

    .content {
      flex: 1;
      overflow: hidden;
    }

    .title {
      font-weight: 700;
      font-size: 14px;
      color: #313238;
      line-height: 22px;
      text-overflow: ellipsis;
      overflow: hidden;
      white-space: nowrap;
      .short-name {
        font-size: 12px;
        color: #979ba5;
      }
    }

    .tag-list {
      .tag {
        height: 16px;
        line-height: 16px;
        padding: 0 4px;
        margin-right: 4px;
        &:last-child {
          margin-right: 0;
        }
      }
    }
  }
}
</style>
