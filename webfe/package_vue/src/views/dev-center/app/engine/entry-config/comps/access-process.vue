<template>
  <div class="approve-container">
    <paas-content-loader
      :is-loading="loaderLoading"
      placeholder="order-loading"
      :offset-top="25"
      class="order-approve-wrapper"
    >
      <div class="process-wrapper">
        <!-- activeName 默认激活项 -->
        <bk-collapse
          v-model="activeName"
          ext-cls="process-collapse-cls"
          :hide-arrow="true"
        >
          <bk-collapse-item
            v-for="(process, index) in processServiceList"
            :name="process.name"
            :key="index"
          >
            <div class="header-warpper">
              <i class="paasng-icon paasng-right-shape"></i>
              <div class="process-info">
                <div class="name">{{ process.process_type }}</div>
                <div class="info">
                  <span>{{ $t('端口规则：') + process.ports.length + $t('个')}}</span>
                </div>
              </div>
              <!-- <div class="right-tip">{{ $t('已暴露 HTTP 服务') }}</div> -->
            </div>
            <div
              slot="content"
              class="f13"
            >
              <!-- 端口配置 -->
              <div class="process-config-item">
                <div class="header">
                  <p>{{ $t('端口配置') }}</p>
                  <!-- 二期 -->
                  <!-- <div class="edit-container">
                    <i class="paasng-icon paasng-edit-2 pl10" />
                    {{ $t('编辑') }}
                  </div> -->
                </div>
                <bk-table
                  :data="process.ports"
                  :outer-border="false"
                  :header-border="false"
                >
                  <bk-table-column
                    :label="$t('端口名称')"
                    prop="source"
                  ></bk-table-column>
                  <bk-table-column
                    :label="$t('协议')"
                    prop="status"
                  ></bk-table-column>
                  <bk-table-column
                    :label="$t('服务端口（prod）')"
                    prop="status"
                  ></bk-table-column>
                  <bk-table-column
                    :label="$t('进程内容端口')"
                    prop="status"
                  ></bk-table-column>
                </bk-table>
              </div>
            </div>
          </bk-collapse-item>
        </bk-collapse>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      loaderLoading: false,
      activeName: ['image4test--web'],
      processServiceList: [
        {
          name: 'image4test--web',
          process_type: 'web',
          ports: [],
        },
      ],
    };
  },
  computed: {},
  created() {
    this.getProcessServiceData();
  },
  methods: {
    setStatus(status) {
      this.orderStatus = status;
    },
    handlerDataReady() {
      this.isLoading = false;
      this.loaderLoading = false;
    },
    async getProcessServiceData() {
      try {
        const res = await this.$store.dispatch('processes/getProcessService', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env: 'stag',
        });
        console.log('proc_services--', res);
        this.processServiceList = res.proc_services || [];
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.process-collapse-cls {
  /deep/ .bk-collapse-item-active .bk-collapse-item-header {
    .header-warpper i.paasng-right-shape {
      transform: rotate(90deg) translate(-50%, 0);
      color: #63656e;
    }
  }

  /deep/ .bk-collapse-item-header {
    height: 64px;
    background: #ffffff;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    font-size: 12px;
    color: #979ba5;
    .header-warpper {
      position: relative;
      height: 100%;
      display: flex;
      justify-content: space-between;

      i.paasng-right-shape {
        position: absolute;
        left: 16px;
        top: 50%;
        transform: translateY(-50%);
        color: #c4c6cc;
        transition: all linear 0.2s;
      }

      .process-info {
        margin: auto 0;
        margin-left: 46px;
        .name {
          font-weight: 700;
          font-size: 14px;
          color: #63656e;
          line-height: 22px;
        }
        .info {
          line-height: 20px;
        }
      }
    }
  }

  /deep/ .fr {
    display: none;
  }

  /deep/ .bk-collapse-item-content {
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-top: none;
    border-radius: 2px;

    padding: 16px 32px;
  }
}
.process-config-item {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px;
    height: 32px;
    background: #f0f1f5;
    p {
      font-weight: 700;
      font-size: 12px;
      color: #63656e;
    }
    .edit-container {
      font-size: 12px;
      cursor: pointer;
      color: #3a84ff;
    }
  }
}
</style>
