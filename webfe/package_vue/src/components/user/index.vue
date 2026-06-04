<template>
  <div>
    <!-- 人员选择器 -->
    <bk-user-selector
      v-if="isMultiTenantDisplayMode || $isInternalVersion"
      ref="bkUserSelector"
      :model-value="localValue"
      v-bind="props"
      :api-base-url="apiBaseUrl"
      :tenant-id="tenantId || 'default'"
      :multiple="multiple"
      @update:modelValue="handleBkUserSelectorInput"
    ></bk-user-selector>
    <template v-else>
      <blueking-user-selector
        v-if="GLOBAL.USERS_URL"
        ref="userSelector"
        v-model="localValue"
        class="cmdb-form-objuser"
        display-list-tips
        v-bind="props"
        @focus="$emit('focus')"
        @blur="$emit('blur')"
      />
      <bk-member-selector
        v-else
        v-bind="props"
        ref="member_selector"
        v-model="localValue"
        :max-data="curMaxData"
        @blur="$emit('blur')"
      />
    </template>
  </div>
</template>

<script>
import BluekingUserSelector from '@blueking/user-selector';
import BkUserSelector from '@blueking/bk-user-selector/vue2';
import { mapGetters } from 'vuex';

export default {
  name: 'CmdbFormObjuser',
  components: {
    BluekingUserSelector,
    'bk-member-selector': () => import('./member-selector/member-selector.vue'),
    BkUserSelector,
  },
  props: {
    value: {
      type: [Array, String],
      default() {
        return [];
      },
    },
    multiple: {
      type: Boolean,
      default: true,
    },
  },
  computed: {
    ...mapGetters(['tenantId', 'isMultiTenantDisplayMode']),
    api() {
      return this.GLOBAL.USERS_URL;
    },
    isBkUserSelectorMode() {
      return this.isMultiTenantDisplayMode || this.$isInternalVersion;
    },
    /**
     * 统一将外部传入的 value 规范化为数组格式
     */
    normalizedValue() {
      const val = this.value;
      if (val === null || val === undefined || val === '') {
        return [];
      }
      if (Array.isArray(val)) {
        return val;
      }
      if (typeof val === 'string') {
        // 兼容历史 string 数据，可能是逗号分隔的多个值
        return val
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
      }
      if (typeof val === 'object') {
        // object 类型（如 { username: 'xxx' }），提取 username 或 id
        return [val.username || val.id || val];
      }
      return [val];
    },
    localValue: {
      get() {
        if (this.isBkUserSelectorMode) {
          // 多租户模式下，bk-user-selector 单选需要字符串，多选需要数组
          if (this.multiple) {
            return this.normalizedValue;
          }
          return this.normalizedValue[0] || '';
        }
        return this.normalizedValue;
      },
      set(val) {
        // 统一将设置的值规范化为数组
        const normalizedVal = this.normalizeToArray(val);

        // 对外统一 emit 数组格式（保持父组件接口兼容：.join(), .length, [0] 等数组操作）
        const currentNormalized = this.normalizedValue;
        const isSame =
          normalizedVal.length === currentNormalized.length &&
          normalizedVal.every((v, i) => v === currentNormalized[i]);

        if (!isSame) {
          this.$emit('input', normalizedVal);
          this.$nextTick(() => {
            this.$emit('change', normalizedVal);
          });
        }
      },
    },
    props() {
      const props = { ...this.$attrs };
      if (this.api) {
        props.api = this.api;
      } else {
        props.fuzzySearchMethod = this.fuzzySearchMethod;
        props.exactSearchMethod = this.exactSearchMethod;
        props.pasteValidator = this.pasteValidator;
      }
      return props;
    },
    curMaxData() {
      return this.multiple ? -1 : 1;
    },
    apiBaseUrl() {
      // 多租户模式
      if (this.isMultiTenantDisplayMode) {
        return window.BK_API_URL_TMPL?.replace('{api_name}', 'bk-user-web/prod');
      }
      // 上云版
      const baseUrl = window.BK_API_URL_TMPL;
      const envPath = window.BK_USER_API_STAGE ? `/${window.BK_USER_API_STAGE}` : '/prod';
      return baseUrl?.includes('{api_name}') ? `${baseUrl.replace('{api_name}', 'bk-user-web')}${envPath}` : baseUrl;
    },
  },
  methods: {
    /**
     * 将任意类型的值规范化为数组
     * @param {any} val - 输入值
     * @returns {Array} - 规范化后的数组
     */
    normalizeToArray(val) {
      if (val === null || val === undefined || val === '') {
        return [];
      }
      if (Array.isArray(val)) {
        return val.filter((item) => item !== null && item !== undefined && item !== '');
      }
      if (typeof val === 'string') {
        return val
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean);
      }
      if (typeof val === 'object') {
        return [val.username || val.id || val];
      }
      return [val];
    },
    handleBkUserSelectorInput(val) {
      this.localValue = val;
    },
    focus() {
      if (this.$refs.userSelector) {
        this.$refs.userSelector.focus();
      } else if (this.$refs.member_selector) {
        this.$refs.member_selector.$el.click();
      }
    },
    async fuzzySearchMethod(keyword, _page = 1) {
      const users = await this.$http.get(`${window.API_HOST}user/list`, {
        params: {
          fuzzy_lookups: keyword,
        },
        config: {
          cancelPrevious: true,
        },
      });
      return {
        next: false,
        results: users.map((user) => ({
          username: user.english_name,
          display_name: user.chinese_name,
        })),
      };
    },
    exactSearchMethod(usernames) {
      const isBatch = Array.isArray(usernames);
      return Promise.resolve(isBatch ? usernames.map((username) => ({ username })) : { username: usernames });
    },
    pasteValidator(usernames) {
      return Promise.resolve(usernames);
    },
  },
};
</script>

<style lang="scss" scoped>
.cmdb-form-objuser {
  width: 100%;
}
</style>
