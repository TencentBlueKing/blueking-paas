<template lang="html">
  <div
    class="right-main order-approve-wrapper"
    style="overflow: hidden; min-height: 500px;"
  >
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="order-loading"
      :offset-top="25"
      class="app-container middle"
    >
      <section v-show="!isLoading">
        <bk-tab
          class="mt5"
          :active.sync="orderStatus"
          type="unborder-card"
        >
          <bk-tab-panel
            name="processing"
            :label="$t('未审批')"
          >
            <processing-order @data-ready="handlerDataReady" />
          </bk-tab-panel>
          <bk-tab-panel
            name="done"
            :label="$t('已审批')"
          >
            <done-order @data-ready="handlerDataReady" />
          </bk-tab-panel>
        </bk-tab>
      </section>
    </paas-content-loader>
  </div>
</template>

<script>import processingOrder from './processing-order';
import doneOrder from './done-order';
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  components: {
    processingOrder,
    doneOrder,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      orderStatus: 'processing',
    };
  },
  computed: {
    curModule() {
      return this.curAppModuleList.find(item => item.is_default);
    },
  },
  watch: {
    '$route'() {
      this.$refs.moduleRef && this.$refs.moduleRef.setCurModule(this.curModule);
      this.isLoading = true;
    },
  },
  mounted() {
    this.$refs.moduleRef && this.$refs.moduleRef.setCurModule(this.curModule);
  },
  methods: {
    setStatus(status) {
      this.orderStatus = status;
    },
    handlerDataReady() {
      this.isLoading = false;
    },
  },
};

</script>

  <style lang="scss" scoped>
      .ps-table-bar {
          padding: 20px 0;
      }

      .ps-checkbox-default {
          vertical-middle: top;
      }

      .ps-table td {
          padding: 14px 0 14px 20px;

          &:first-child {
              padding-left: 30px;
          }
      }
  </style>

