<template lang="html">
  <bk-dialog
    v-model="visible"
    theme="primary"
    :width="845"
    :mask-close="false"
    header-position="left"
    ext-cls="paasng-api-batch-apply-dialog"
    :title="$t(title)"
    @after-leave="handleAfterLeave"
  >
    <div class="content">
      <paasng-alert>
        <div slot="title">
          <span v-dompurify-html="alertTxt"></span>
          {{ renewalRows.length > 0 ? '，' : '。' }}
          <template v-if="renewalRows.length > 0">
            <span style="color: #ff9c01">{{ renewalRows.length }}</span>
            {{ $t('个网关 API 已有权限，不可重复申请。') }}
          </template>
        </div>
      </paasng-alert>
      <div class="api-batch-apply-content">
        <table class="bk-table api-batch-apply-fixed-table">
          <colgroup>
            <col style="width: 200px" />
            <col style="width: 200px" />
            <col />
          </colgroup>
          <thead>
            <tr>
              <th style="padding-left: 20px">
                {{ isComponent ? $t('系统') : $t('网关') }}
              </th>
              <th>API</th>
              <th>{{ $t('描述') }}</th>
            </tr>
          </thead>
        </table>
        <div
          ref="apiTableRef"
          :class="['api-batch-apply-table', { 'has-bottom-border': !isScrollBottom && rows.length > 4 }]"
          @scroll.stop="handleScroll($event)"
        >
          <table class="bk-table has-table-hover">
            <colgroup>
              <col style="width: 200px" />
              <col style="width: 200px" />
              <col />
            </colgroup>
            <tbody style="background: #fff">
              <template v-if="rows.length > 0">
                <tr
                  v-for="(item, index) in rows"
                  :key="index"
                >
                  <td style="text-align: left; padding-left: 20px">
                    <span class="name">{{ isComponent ? item.system_name : item.api_name }}</span>
                  </td>
                  <td>
                    <span
                      class="api-batch-apply-name"
                      :title="item.name"
                    >
                      {{ item.name }}
                    </span>
                  </td>
                  <td>
                    <span
                      class="desc"
                      :title="item.description ? item.description : ''"
                    >
                      <template v-if="item.permission_action === 'renew'">
                        <span style="color: #ff9c01">{{ $t('已有权限，不可重复申请') }}</span>
                      </template>
                      <template v-else>
                        {{ item.description || '--' }}
                      </template>
                    </span>
                  </td>
                </tr>
              </template>
              <template v-if="rows.length < 1">
                <tr>
                  <td colspan="3">
                    <div class="search-empty-wrapper">
                      <div class="empty-wrapper">
                        <i class="bk-icon icon-empty" />
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
      <bk-form
        :label-width="localLanguage === 'en' ? 110 : 80"
        :model="formData"
        style="margin-top: 25px"
      >
        <bk-form-item
          :label="$t('申请理由')"
          required
          property="reason"
        >
          <bk-input
            v-model="formData.reason"
            type="textarea"
            :maxlength="120"
          />
        </bk-form-item>
        <bk-form-item
          :label="$t('有效时间')"
          required
          property="expired"
        >
          <bk-radio-group v-model="formData.expired">
            <bk-radio-button :value="6">
              {{ $t('6个月') }}
            </bk-radio-button>
            <bk-radio-button :value="12">
              {{ $t('12个月') }}
            </bk-radio-button>
            <bk-radio-button :value="0">
              {{ $t('永久') }}
            </bk-radio-button>
          </bk-radio-group>
        </bk-form-item>
      </bk-form>
    </div>
    <template slot="footer">
      <bk-button
        theme="primary"
        :disabled="formData.reason === ''"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        style="margin-left: 10px"
        @click="handleCancel"
      >
        {{ $t('取消') }}
      </bk-button>
    </template>
  </bk-dialog>
</template>
<script>
import PaasngAlert from './paasng-alert';
import i18n from '@/language/i18n';
export default {
  name: '',
  components: {
    PaasngAlert,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: i18n.t('批量申请权限'),
    },
    rows: {
      type: Array,
      default: () => [],
    },
    appCode: {
      type: String,
      default: '',
    },
    apiId: {
      type: [String, Number],
      default: '',
    },
    apiName: {
      type: String,
      default: '',
    },
    isComponent: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      visible: false,
      loading: false,
      formData: {
        reason: '',
        expired: 12,
      },
      isScrollBottom: false,
    };
  },
  computed: {
    // 可申请
    applyRows() {
      return this.rows.filter((item) => !item.applyDisabled);
    },
    // 可续期
    renewalRows() {
      return this.rows.filter((item) => !item.renewDisabled);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    alertTxt() {
      return this.$t('将申请{t} {n} 下 <i class="l1">{l}</i> 个{y}API的权限', {
        t: this.isComponent ? this.$t('系统') : this.$t('网关'),
        n: this.apiName,
        l: this.applyRows.length,
        y: this.isComponent ? this.$t('组件') : this.$t('网关'),
      });
    },
  },
  watch: {
    show: {
      handler(value) {
        this.visible = !!value;
      },
      immediate: true,
    },
  },
  methods: {
    async handleConfirm() {
      this.loading = true;
      try {
        const params = {
          data: {
            reason: this.formData.reason,
            expire_days: this.formData.expired * 30,
            gateway_name: this.apiName,
          },
          appCode: this.appCode,
        };
        if (this.isComponent) {
          params.data.component_ids = this.applyRows.map((item) => item.id);
          params.systemId = this.apiId;
        } else {
          params.data.resource_ids = this.applyRows.map((item) => item.id);
          params.data.grant_dimension = 'resource';
          params.apiId = this.apiId;
        }
        const methods = this.isComponent ? 'sysApply' : 'apply';
        await this.$store.dispatch(`cloudApi/${methods}`, params);
        this.$emit('on-apply');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
      }
    },

    handleCancel() {
      this.visible = false;
    },

    handleAfterLeave() {
      this.formData = Object.assign(
        {},
        {
          reason: '',
          expired: 6,
        }
      );
      this.$emit('update:show', false);
      this.$emit('after-leave');
    },

    handleScroll(event) {
      if (event.target.scrollTop + event.target.offsetHeight >= event.target.scrollHeight) {
        this.isScrollBottom = true;
      } else {
        this.isScrollBottom = false;
      }
    },
  },
};
</script>
<style lang="scss">
.paasng-api-batch-apply-dialog {
  .l1 {
    color: #2dcb56;
    font-style: normal;
  }
  .api-batch-apply-content {
    position: relative;
    margin-top: 10px;
  }
  .api-batch-apply-fixed-table {
    width: 100%;
    border-top: 1px solid #e6e6e6;
    border-left: 1px solid #e6e6e6;
    border-right: 1px solid #e6e6e6;
    border-bottom: none;
    thead {
      tr {
        th {
          height: 42px;
          font-size: 12px;
          background: #f5f6fa;
          .bk-form-checkbox .bk-checkbox-text {
            font-size: 12px;
          }
        }
      }
    }
  }
  .api-batch-apply-table {
    position: relative;
    width: 100%;
    max-height: 200px;
    margin-top: -1px;
    overflow-y: auto;
    border-left: 1px solid #e6e6e6;
    border-right: 1px solid #e6e6e6;
    border-bottom: none;
    &.has-bottom-border {
      border-bottom: 1px solid #e6e6e6;
    }
    &::-webkit-scrollbar {
      width: 4px;
      background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
      height: 5px;
      border-radius: 2px;
      background-color: #e6e9ea;
    }
    .bk-table {
      width: 100%;
      border: none;
      thead {
        tr {
          th {
            height: 42px;
            font-size: 12px;
          }
        }
      }
      tbody {
        tr {
          position: relative;
          td {
            height: 42px;
            font-size: 12px;
          }
        }
        .search-empty-wrapper {
          position: relative;
          min-height: 200px;
          .empty-wrapper {
            position: absolute;
            left: 50%;
            top: 50%;
            text-align: center;
            transform: translate(-50%, -50%);
            i {
              font-size: 50px;
              color: #c3cdd7;
            }
          }
        }
      }
      .api-batch-apply-name,
      .name {
        display: inline-block;
        max-width: 140px;
        font-size: 12px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        vertical-align: middle;
      }
      .desc {
        display: inline-block;
        max-width: 200px;
        font-size: 12px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        vertical-align: middle;
      }
    }
  }
}
</style>
