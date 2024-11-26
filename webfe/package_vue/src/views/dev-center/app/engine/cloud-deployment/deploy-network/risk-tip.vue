<template>
  <div class="risk">
    <bk-alert
      type="error"
      :show-icon="false"
    >
      <div
        slot="title"
        class="risk-alert"
      >
        <i class="paasng-icon paasng-paas-remind-fill" />
        {{
          $t(
            '当前值由应用描述文件（app_desc.yaml）定义。如果应用描述文件中的定义没有被删除，在部署时将覆盖您在产品上填写的值。'
          )
        }}
      </div>
    </bk-alert>
    <app-description :doc="doc" />
  </div>
</template>

<script>
import appDescription from './app-description.vue';
export default {
  components: { appDescription },
  props: {
    doc: {
      type: String,
      default: '',
    },
  },
};
</script>

<style lang="scss" scoped>
.risk {
  margin-bottom: 16px;
}
.risk-alert {
  i {
    color: #ea3636;
    margin-right: 8px;
    font-size: 16px;
    transform: translateY(0);
  }
}
</style>
