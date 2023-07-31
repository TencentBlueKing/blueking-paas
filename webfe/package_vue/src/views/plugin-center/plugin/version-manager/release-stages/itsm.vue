<template>
  <div class="itsm">
    <status-bar :type="curStatusBarData.type">
      <template v-slot:left>
        <!-- 等待审批 -->
        <span class="warning-check-wrapper" v-if="curStatusBarData.type === 'warning'">
          <i class="paasng-icon paasng-paas-remind-fill" />
        </span>
        <!-- 审批通过 -->
        <span class="success-check-wrapper" v-else-if="curStatusBarData.type === 'success'">
          <i class="paasng-icon paasng-correct" />
        </span>
        <!-- 审批不通过 -->
        <span class="error-left-warp flex-row align-items-center" v-else-if="curStatusBarData.type === 'failed'">
          <i class="error-icon paasng-icon paasng-close-circle-shape" />
        </span>
        <!-- 撤销提单 -->
        <span class="interrupted-check-wrapper" v-else>
          <i class="paasng-icon paasng-back2" />
        </span>
        <span class="info-time pl10">
          <span class="info-pending-text"> {{ curStatusBarData.title }} </span>
        </span>
      </template>
      <template v-slot:right>
        <bk-button
          size="small"
          theme="primary"
          :outline="true"
          ext-cls="detail-btn"
          @click="handlerApprovalDetails"
        >
          {{ $t('查看审批详情') }}
        </bk-button>
        <bk-button
          v-if="isCancelBtn"
          size="small"
          theme="primary"
          :outline="true"
          class="ml8"
          ext-cls="detail-btn"
          @click="handlerApprovalDetails"
        >
          {{ $t('撤销提单') }}
        </bk-button>
      </template>
    </status-bar>
    
    <itsm-info-item :title="$t('提单信息')" :data="ladingData"></itsm-info-item>
    <itsm-info-item :title="$t('申请内容')" :data="applyData"></itsm-info-item>
  </div>
</template>
<script>
  import stageBaseMixin from './stage-base-mixin';
  import statusBar from './comps/status-bar';
  import itsmInfoItem from './comps/itsm-info-item';
  import i18n from '@/language/i18n';
  import { PLUGIN_ITSM_APPLY, PLUGIN_ITSM_LADING } from '@/common/constants';

  // 提单信息
  const ladingMap = PLUGIN_ITSM_LADING;

  // 申请内容
  const applyMap = PLUGIN_ITSM_APPLY;

  const approvalStatus = {
    'pending': 'approval',
    'initial': 'approval',
    'successful': 'successful',
    'failed': 'failed',
    'interrupted': 'interrupted',
  };

  const statusBarData = {
    'approval': {
      title: i18n.t('等待审批'),
      type: 'warning',
    },
    'successful': {
      title: i18n.t('审批通过'),
      type: 'success',
    },
    'failed': {
      title: i18n.t('审批不通过'),
      type: 'failed',
    },
    'interrupted': {
      title: i18n.t('已撤销提单'),
      type: 'interrupted',
    }
  };

  export default {
    mixins: [stageBaseMixin],
    components: {
      statusBar,
      itsmInfoItem
    },
    props: {
      pluginData: {
        type: Object,
        default: () => {}
      },
      stageData: {
        type: Object,
        default: () => {}
      }
    },
    data () {
      return {
        ladingData: [],
        applyData: []
      };
    },
    computed: {
      itsmData () {
        return this.pluginData.current_stage.itsm_detail?.fields || [];
      },
      itsmDetail () {
        return this.pluginData.current_stage?.itsm_detail || {};
      },
      curStatusBarData () {
        // approval successful failed interrupted
        const curStatus = approvalStatus[this.pluginData.current_stage.status];
        return statusBarData[curStatus];
      },
      isCancelBtn () {
        return this.stageData.detail?.can_withdraw;
      }
    },
    watch: {
      itsmData () {
        this.init();
      }
    },
    mounted () {
      this.init();
    },
    methods: {
      init () {
        if (this.ladingData.length && this.applyData.length) {
          return;
        }
        this.itsmData.forEach(item => {
          if (ladingMap[item.key]) {
            const data = { ...item, name: ladingMap[item.key] };
            this.ladingData.unshift(data);
          }
          if (applyMap[item.key]) {
            const data = { ...item, name: applyMap[item.key] };
            this.applyData.push(data);
          }
        });
        this.ladingData.unshift({
          name: '单号',
          value: this.itsmDetail['sn']
        });
      },
      // 查看详情
      handlerApprovalDetails () {
        window.open(this.itsmDetail['ticket_url'], '_blank');
      }
    }
  };
</script>

<style lang="scss" scoped>
  .itsm {
    margin-top: 60px;
    margin-bottom: 80px;

    .wrapper {
      .bk-button.bk-primary.is-outline.detail-btn {
        background: transparent;

        &:hover {
          background: #3a84ff;
          border-color: #3a84ff;
          color: #fff;
        }
      }

      .ml8 {
        margin-left: 8px;
      }

      .error-left-warp {
        i {
          font-size: 24px;
        }
      }
    }
  }
</style>
