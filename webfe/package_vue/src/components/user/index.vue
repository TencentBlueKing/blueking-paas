<template>
  <div :class="localValue">
    <!-- 多租户人员选择器 -->
    <bk-user-selector
      v-if="isMultiTenantDisplayMode"
      ref="bkUserSelector"
      v-model="localValue"
      v-bind="props"
      :api-base-url="apiBaseUrl"
      :tenant-id="tenantId"
      :multiple="multiple"
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
      type: Array,
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
    localValue: {
      get() {
        if (this.isMultiTenantDisplayMode) {
          // 多租户
          if (this.multiple) {
            return this.value;
          } else {
            return Array.isArray(this.value) ? this.value[0] : this.value;
          }
        }
        return this.value;
      },
      set(val) {
        if (this.isMultiTenantDisplayMode) {
          // 处理多租户单选、多选差异
          if (this.multiple) {
            this.$emit('input', val);
          } else {
            this.$emit('input', Array.isArray(val) ? [val[0]] : [val]);
          }
        } else {
          this.$emit('input', val); // 非多租户情况下，保持数组
        }
        this.$nextTick(() => {
          this.$emit('change', this.value, val.toString);
        });
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
      return window.BK_API_URL_TMPL?.replace('{api_name}', 'bk-user-web/prod');
    },
  },
  methods: {
    focus() {
      if (this.$refs.userSelector) {
        this.$refs.userSelector.focus();
      } else if (this.$refs.member_selector) {
        this.$refs.member_selector.$el.click();
      }
    },
    async fuzzySearchMethod(keyword, page = 1) {
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
