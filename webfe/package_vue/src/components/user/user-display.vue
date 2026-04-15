<template>
  <span class="user-display-wrapper">
    <!-- 多租户模式：使用 bk-user-display-name 渲染 -->
    <template v-if="isMultiTenantDisplayMode && hasUserIds">
      <!-- 单个用户 -->
      <bk-user-display-name v-if="isSingle" :user-id="value" />
      <!-- 多个用户 -->
      <template v-else-if="isArray">
        <span v-for="(item, index) in value" :key="item" class="user-display-item">
          <bk-user-display-name :user-id="item" />
          <span v-if="index < value.length - 1" class="user-display-sep">{{ separator }}</span>
        </span>
      </template>
      <!-- 对象 -->
      <bk-user-display-name v-else-if="isObject" :user-id="displayId" />
    </template>

    <!-- 非多租户模式 / 无有效数据：显示纯文本 -->
    <template v-else>{{ plainText }}</template>
  </span>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'UserDisplay',
  props: {
    /**
     * 用户数据，支持三种类型：
     *  - String: 单个用户 ID，如 'admin'
     *  - Array:  用户 ID 数组，如 ['admin', 'test']
     *  - Object: 用户对象，如 { username: 'admin', display_name: '管理员' }
     */
    value: {
      type: [String, Array, Object],
      default: '',
    },
    /**
     * 非多租户模式下的自定义回退文本，优先级高于 value
     * 适用场景：如 paas-header 中 user.chineseName || user.username
     */
    fallback: {
      type: String,
      default: undefined,
    },
    /** 空值时的占位文本 */
    emptyText: {
      type: String,
      default: '--',
    },
    /** 数组分隔符 */
    separator: {
      type: String,
      default: '\uff0c',
    },
    /** 对象类型时取哪个字段作为显示文本（非多租户模式） */
    displayField: {
      type: String,
      default: 'username',
    },
    /** 对象类型时取哪个字段作为 user-id（多租户模式） */
    idField: {
      type: String,
      default: 'username',
    },
  },
  computed: {
    ...mapGetters(['isMultiTenantDisplayMode']),

    /** 值类型判断 */
    isSingle() {
      return typeof this.value === 'string';
    },
    isArray() {
      return Array.isArray(this.value);
    },
    isObject() {
      return this.value !== null && typeof this.value === 'object' && !Array.isArray(this.value);
    },

    /** 是否存在有效的用户 ID（用于决定是否走多租户渲染） */
    hasUserIds() {
      if (this.isSingle) return !!this.value;
      if (this.isArray) return this.value.length > 0;
      if (this.isObject) return !!this.displayId;
      return false;
    },

    /** 对象类型：多租户模式使用的 user-id */
    displayId() {
      return this.isObject ? (this.value[this.idField] || '') : '';
    },

    /**
     * 非多租户模式下的纯文本
     * 优先级: fallback > 类型对应的文本 > emptyText
     */
    plainText() {
      if (this.fallback !== undefined) return this.fallback;
      if (this.isSingle) return this.value || this.emptyText;
      if (this.isArray) {
        const joined = this.value.filter(Boolean).join(this.separator);
        return joined || this.emptyText;
      }
      if (this.isObject) {
        return this.value[this.displayField] || this.emptyText;
      }
      return this.emptyText;
    },
  },
};
</script>

<style scoped>
.user-display-wrapper {
  display: inline;
}
.user-display-item {
  display: inline;
}
</style>
