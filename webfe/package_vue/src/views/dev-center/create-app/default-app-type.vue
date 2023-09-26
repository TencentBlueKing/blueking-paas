<template lang="html">
  <div class="container">
    <div class="create-item">
      <div class="item-title">
        {{ $t('代码来源') }}
      </div>
      <div
        id="choose-cluster"
        class="form-group-dir"
      >
        <div
          class="tab-box mt10"
        >
          <li
            v-for="app in appTypeList"
            :key="app.type"
            :class="['tab-item', { 'active': appType === app.type }]"
            @click="handleToggleType(app.type)"
          >
            {{ app.title }}
          </li>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import i18n from '@/language/i18n.js';
const DEFAULT_APP_TYPE = [
  {
    title: i18n.t('代码仓库'),
    type: 'default',
  },
  {
    title: i18n.t('蓝鲸可视化开发平台'),
    type: 'bkLesscode',
  },
];

export default {
  props: {
    displayLesscode: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      appType: 'default',
      typeList: DEFAULT_APP_TYPE,
    };
  },
  computed: {
    userFeature() {
      return this.$store.state.userFeature;
    },
    // 过滤字段控制的smart应用
    appTypeList() {
      const list = [...this.typeList];
      if (this.userFeature.ALLOW_CREATE_SMART_APP) {
        list.push({
          title: this.$t('S-mart 应用'),
          type: 'smart',
        });
      }
      return list;
    },
  },
  methods: {
    handleToggleType(type) {
      this.$emit('on-change-type', type);
      this.appType = type;
    },
  },
};
</script>

<style lang="scss" scoped>
    @import './default.scss';
    @import '~@/assets/css/mixins/border-active-logo.scss';
    .container {
        width: 1200px;
        margin: auto;
        .create-item {
            width: 100%;
            .form-group-dir {
                display: block
            }
        }
    }
    .tab-box {
        margin: auto;
        height: 56px;
        list-style: none;
        display: flex;

        .tab-item {
            flex: 1;
            margin-right: 16px;
            height: 56px;
            line-height: 56px;
            text-align: center;
            background: #f0f1f5;
            border-radius: 2px;
            font-size: 14px;
            color: #63656e;
            cursor: pointer;
            position: relative;

            &:last-of-type {
                margin-right: 0 !important;
            }

            &.active {
                background: #fff;
                border: 2px solid #3a84ff;
                color: #3a84ff;

                @include border-active-logo;
            }
        }
    }
</style>
