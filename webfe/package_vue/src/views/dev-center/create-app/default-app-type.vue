<template>
  <div class="container">
    <div class="create-item">
      <div class="item-title">
        {{ $t('代码来源') }}
      </div>
      <div
        id="choose-cluster"
        class="form-group-dir"
      >
        <ul class="tab-box mt10">
          <li
            v-for="app in visibleAppTypes"
            :key="app.type"
            :class="['tab-item', { active: appType === app.type }]"
            @click="handleToggleType(app.type)"
          >
            {{ app.title }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      appType: 'default',
    };
  },
  computed: {
    userFeature() {
      return this.$store.state.userFeature;
    },
    appTypeList() {
      return [
        {
          title: this.$t('代码仓库'),
          type: 'default',
          isShow: true,
        },
        {
          title: this.$t('镜像仓库'),
          type: 'image',
          isShow: true,
        },
        {
          title: this.$t('蓝鲸运维开发平台'),
          type: 'bkLesscode',
          isShow: this.userFeature.BK_LESSCODE_APP,
        },
        {
          title: this.$t('S-mart 应用'),
          type: 'smart',
          isShow: this.userFeature.ALLOW_CREATE_SMART_APP,
        },
      ];
    },
    visibleAppTypes() {
      return this.appTypeList.filter((app) => app.isShow);
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
      display: block;
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
