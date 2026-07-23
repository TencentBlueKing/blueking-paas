<template>
  <BkLoginUserinfo
    :userinfo="loginUserInfo"
    :action-list="actionList"
    :render-slot="renderSlot"
  />
</template>

<script>
import auth from '@/auth';
import BkLoginUserinfo from '@blueking/login-userinfo/vue2';
import { mapState } from 'vuex';
import '@blueking/login-userinfo/vue2/vue2.css';

// 兼容接口原始 snake_case 字段和 auth 模块转换后的 camelCase 字段。
const USER_FIELD_KEYS = {
  displayName: ['username', 'displayName', 'display_name'],
  tenant: ['tenantId', 'tenant_id'],
  timezone: ['timeZone', 'time_zone'],
  personalCenterUrl: ['personalCenterUrl', 'personal_center_url'],
};

export default {
  name: 'PaasLoginUserinfo',
  components: {
    BkLoginUserinfo,
  },
  props: {
    user: {
      type: Object,
      default: () => ({}),
    },
  },
  computed: {
    ...mapState(['platformFeature']),
    loginUserInfo() {
      const userinfo = {
        name: this.displayName,
      };

      // 企业空间
      if (this.platformFeature.MULTI_TENANT_MODE) {
        const organization = this.getUserValue(USER_FIELD_KEYS.tenant) || '--';
        userinfo.organization = this.formatOrganization(organization);
      }

      // 当前时区
      const timezone = this.getUserValue(USER_FIELD_KEYS.timezone, [this.user]);
      if (timezone) {
        userinfo.timezone = timezone;
      }
      return userinfo;
    },
    displayName() {
      return this.getUserValue(USER_FIELD_KEYS.displayName) || '--';
    },
    // 个人设置
    personalCenterUrl() {
      return this.getUserValue(USER_FIELD_KEYS.personalCenterUrl);
    },
    actionList() {
      const logoutAction = {
        text: this.$t('退出登录'),
        theme: 'danger',
        icon: 'paasng-icon paasng-export',
        handle: () => {
          this.$emit('logout');
        },
      };
      if (!this.platformFeature.MULTI_TENANT_MODE || !this.personalCenterUrl) {
        return [logoutAction];
      }
      return [
        {
          text: this.$t('个人设置'),
          icon: 'paasng-icon paasng-user-line',
          href: this.personalCenterUrl,
          target: '_blank',
        },
        logoutAction,
      ];
    },
  },
  methods: {
    getUserValue(fields, sources = [this.user, auth.getCurrentUser()]) {
      for (const source of sources) {
        if (!source) {
          continue;
        }
        for (const field of fields) {
          const value = source[field];
          const normalizedValue = value === null || value === undefined ? '' : String(value).trim();
          if (normalizedValue) {
            return normalizedValue;
          }
        }
      }
      return '';
    },
    formatOrganization(value) {
      // login-userinfo 会隐藏值为 default 的 organization，这里补零宽字符保证非多租户默认空间可见。
      return value === 'default' ? 'default\u200b' : value;
    },
    renderSlot(h) {
      if (!this.platformFeature.MULTI_TENANT_MODE) {
        return this.displayName;
      }
      // 多租户模式下，使用 bk-user-display-name 组件展示用户名
      const username = this.getUserValue(['username']);
      return username ? h('bk-user-display-name', { 'user-id': username }) : this.displayName;
    },
  },
};
</script>
