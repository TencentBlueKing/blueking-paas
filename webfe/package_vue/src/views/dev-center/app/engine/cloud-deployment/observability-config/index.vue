<template>
  <div class="observability-config">
    <div class="top-title mb20">
      <h4>{{ $t('日志采集') }}</h4>
      <p class="tips">
        {{ $t('默认已采集和清洗：标准输出、开发框架定义日志路径中的日志，也可以添加自定义日志采集规则。') }}
      </p>
    </div>
    <!-- 采集规则 -->
    <section class="collection-rules">
      <bk-button
        theme="primary"
        class="mb16"
        @click="handleAddCollectionRule"
      >
        <i class="paasng-icon paasng-plus mr5" />
        {{ $t('新增采集规则') }}
      </bk-button>
      <bk-table
        v-bkloading="{ isLoading: isTableLoading }"
        :data="logCollectionList"
        :size="'small'"
        ext-cls="collection-rules-cls"
        :outer-border="false"
        :header-border="false"
        :pagination="pagination"
        @page-change="handlePageChange"
        @page-limit-change="handleLimitChange"
      >
        <div slot="empty">
          <table-empty
            :explanation="$t('当前模块任意环境部署成功后，将会给该模块配置默认的日志采集规则。')"
            empty
          />
        </div>
        <bk-table-column
          :label="$t('采集规则名称')"
          :show-overflow-tooltip="true"
        >
          <div
            slot-scope="{ row }"
            class="strategy-name"
            @click="handleToLink(row)"
          >
            {{ row.name_en }}
          </div>
        </bk-table-column>
        <bk-table-column
          :label="$t('采集对象')"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row }">
            {{ row.log_type === 'stdout' ? $t('标准输出') : $t('容器内文件') }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('日志采集路径')"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row }">
            <div v-if="row.log_paths && row.log_paths.length">{{ row.log_paths.join('; ') }}</div>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('类型')">
          <template slot-scope="{ row }">
            {{ row.is_builtin ? $t('平台内置') : $t('自定义') }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('操作')"
          width="150"
        >
          <template slot-scope="{ row }">
            <span v-bk-tooltips="{ content: $t('不能操作平台内置规则'), disabled: !row.is_builtin }">
              <bk-button
                class="mr10"
                theme="primary"
                text
                :disabled="row.is_builtin"
                @click="handleCollectionRuleEdit(row)"
              >
                {{ $t('编辑') }}
              </bk-button>
            </span>
            <span v-bk-tooltips="{ content: $t('不能操作平台内置规则'), disabled: !row.is_builtin }">
              <bk-button
                theme="primary"
                text
                :disabled="row.is_builtin"
                @click="handleCollectionRuleDelete(row)"
              >
                {{ $t('删除') }}
              </bk-button>
            </span>
          </template>
        </bk-table-column>
      </bk-table>
    </section>

    <!-- 告警策略 -->
    <alarm-strategy />

    <!-- 新建采集规则弹窗 -->
    <bk-dialog
      v-model="collectionRulesConfig.visible"
      theme="primary"
      :width="640"
      :mask-close="false"
      :auto-close="false"
      :header-position="collectionRulesConfig.headerPosition"
      :title="$t('新增采集规则')"
      @confirm="hanleConfirm"
      @cancel="hanleDataReset"
    >
      <bk-alert
        class="mb10"
        type="error"
        :title="$t('采集规则新增、编辑后，需要重新部署应用才能生效。')"
      ></bk-alert>
      <bk-form
        :label-width="200"
        :model="formData"
        :rules="rules"
        form-type="vertical"
        ref="validateForm"
      >
        <bk-form-item
          :label="$t('采集规则')"
          :required="true"
          :rules="rules.rule"
          :property="'ruleId'"
          :error-display-type="'normal'"
        >
          <!-- 编辑禁用 -->
          <bk-select v-model="formData.ruleId" :disabled="!collectionRulesConfig.isCreate">
            <bk-option
              v-for="option in collectionRules"
              :key="option.collector_config_id"
              :id="option.collector_config_id"
              :name="option.name_en"
            ></bk-option>
            <div
              slot="extension"
              style="cursor: pointer;text-align: center;"
              @click="handleToLink(customCollectorData)"
            >
              <i class="bk-icon icon-plus-circle"></i>
              {{ $t('新增采集规则') }}
            </div>
          </bk-select>
        </bk-form-item>
        <bk-form-item
          :label="$t('采集对象')"
          :required="true"
          :rules="rules.object"
          :property="'logType'"
          :error-display-type="'normal'"
        >
          <bk-radio-group v-model="formData.logType">
            <!-- 编辑状态，禁止切换采集对象 -->
            <bk-radio :value="'json'">{{ $t('容器内文件') }}</bk-radio>
            <bk-radio :value="'stdout'" :disabled="true">{{ $t('标准输出') }}</bk-radio>
          </bk-radio-group>
        </bk-form-item>
        <!-- 日志采集路径 -->
        <bk-form-item
          :label="$t('日志采集路径')"
          :desc="$t('只支持星号（*）通配符')"
          :desc-type="'border'"
          v-for="(path, index) in formData.logPaths"
          :required="true"
          :rules="rules.path"
          :icon-offset="55"
          :property="'logPaths.' + index + '.value'"
          :key="index"
          :class="{ 'hide-path-cls': index !== 0 }"
          ext-cls="collection-path"
        >
          <bk-input v-model="path.value">
            <template slot="append">
              <i
                class="icon paasng-icon paasng-plus-circle-shape ml10"
                @click="addPath"
              ></i>
              <i
                class="icon paasng-icon paasng-minus-circle-shape ml10"
                :class="{ 'disabled': formData.logPaths.length < 2 }"
                @click="deletePath(index)"
              ></i>
            </template>
          </bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>
  </div>
</template>

<script>import i18n from '@/language/i18n.js';
import alarmStrategy from './alarm-strategy.vue';
export default {
  components: { alarmStrategy },
  data() {
    return {
      isTableLoading: false,
      logCollectionList: [],
      customCollectorData: {},
      pagination: {
        // 页面
        current: 1,
        // 条目总数
        count: 0,
        limit: 10,
      },
      collectionRulesConfig: {
        visible: false,
        headerPosition: 'left',
        isCreate: true,
      },
      // 采集规则数据
      formData: {
        ruleId: '',
        // 新建默认
        logType: 'json',
        logPaths: [
          {
            value: '',
          },
        ],
      },
      rules: {
        rule: [
          {
            required: true,
            message: this.$t('请选择采集规则'),
            trigger: 'blur',
          },
        ],
        object: [
          {
            required: true,
            message: this.$t('请选择采集对象'),
            trigger: 'blur',
          },
        ],
        path: [
          {
            required: true,
            message: this.$t('请输入日志采集路径'),
            trigger: 'blur',
          },
          {
            regex: /^(\/[^/\0]+)+\/?$/,
            message: this.$t('请输入正确路径格式'),
            trigger: 'blur',
          },
        ],
      },
      collectionRules: [],
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    curModuleId() {
      return this.curAppModule?.name;
    },
  },
  created() {
    this.getLogCollectionRuleList();
    this.getCustomLogCollectionRule();
  },
  methods: {
    // 获取日志采集规则列表
    async getLogCollectionRuleList() {
      this.isTableLoading = true;
      try {
        const list = await this.$store.dispatch('observability/getLogCollectionRuleList', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          // appCode: 'test-fastapi',
        });
        this.logCollectionList = list || [];
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
      }
    },

    // 新增/编辑采集信息
    async editorCollectionRule() {
      const paths = this.formData.logPaths.map(v => v.value);
      const collector = this.collectionRules.find(v => v.collector_config_id === this.formData.ruleId);
      const params = {
        name_en: collector.name_en,
        collector_config_id: collector.collector_config_id,
        log_paths: paths,
        log_type: this.formData.logType,
      };
      try {
        await this.$store.dispatch('observability/editorCollectionRule', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: params,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('新增成功'),
        });
        this.collectionRulesConfig.visible = false;
        // 表单数据重置
        this.hanleDataReset();
        this.getLogCollectionRuleList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: `${this.$t('新增失败：')} ${e.detail}`,
        });
      }
    },

    // 删除采集规则
    async deleteCollectionRule(name) {
      try {
        await this.$store.dispatch('observability/deleteCollectionRule', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          name,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.getLogCollectionRuleList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: `${this.$t('删除失败：')} ${e.detail}`,
        });
      }
    },

    // 获取自定义日志采集规则
    async getCustomLogCollectionRule() {
      try {
        const res = await this.$store.dispatch('observability/getCustomLogCollectionRule', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.customCollectorData = res;
        this.collectionRules = res.options || [];
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 新增采集规则
    handleAddCollectionRule() {
      this.getCustomLogCollectionRule();
      this.collectionRulesConfig.visible = true;
      this.collectionRulesConfig.isCreate = true;
    },

    // 编辑采集规则
    handleCollectionRuleEdit(data) {
      // 采集路径
      const paths = data.log_paths.map(v => ({ value: v }));
      if (!paths.length) {
        paths.push({ value: '' });
      }
      // 采集规则列表
      this.collectionRules = [{ ...data }];
      this.formData.ruleId = data.collector_config_id;
      this.formData.logType = data.log_type;
      this.formData.logPaths = paths;
      this.collectionRulesConfig.visible = true;
      this.collectionRulesConfig.isCreate = false;
    },

    // 添加采集路径
    addPath() {
      this.formData.logPaths.push({ value: '' });
    },

    // 移除采集路径
    deletePath(index) {
      if (this.formData.logPaths.length < 2) {
        return;
      }
      this.formData.logPaths.splice(index, 1);
    },

    // 采集规则删除弹窗
    handleCollectionRuleDelete(data) {
      const h = this.$createElement;
      this.$bkInfo({
        extCls: 'delete-collection-rule',
        title: this.$t('是否删除采集规则？'),
        subHeader: h('div', {
          style: {
            textAlign: 'center',
          },
        }, [
          h('div', {
            style: {
              color: '#313238',
            },
          }, i18n.t('采集规则：') + data.name_en),
          h('div', {
            style: {
              marginTop: '8px',
              color: '#63656E',
            },
          }, i18n.t('删除后，将不再采集相关日志。')),
        ]),
        confirmFn: () => {
          this.deleteCollectionRule(data.name_en);
        },
      });
    },

    // 确定、表单校验
    hanleConfirm() {
      this.$refs.validateForm.validate().then(() => {
        this.editorCollectionRule();
      }, (validator) => {
        console.error(validator.content);
      });
    },

    // form表单数据重置
    hanleDataReset() {
      // 清除错误提示
      this.$refs.validateForm?.clearError();
      // 定时器解决 dialog 动画消失时，radio切换视觉问题
      setTimeout(() => {
        this.formData = {
          ruleId: '',
          logType: 'json',
          logPaths: [
            { value: '' },
          ],
        };
      }, 300);
    },

    // 页码变化回调
    handlePageChange(page) {
      this.pagination.current = page;
    },

    // 页容量变化回调
    handleLimitChange(currentLimit) {
      console.log('currentLimit', currentLimit);
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

    handleToLink(row) {
      window.open(row.url, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.observability-config {
  padding: 0 24px 24px 24px;
  .top-title {
    font-size: 12px;
    display: flex;
    align-content: center;
    color: #979ba5;

    h4 {
      font-size: 14px;
      color: #313238;
      padding: 0;
      margin-right: 16px;
      font-weight: 400;
    }
  }

  .strategy-name {
    cursor: pointer;
    color: #3a84ff;
  }

  .collection-rules {
    padding-bottom: 20px;
    border-bottom: 1px solid #eaebf0;
  }
}
.collection-path {
  /deep/ .group-append {
    border: none;
    display: flex;
    align-items: center;
    i {
      font-size: 14px;
      color: #C4C6CC;
      cursor: pointer;

      &.disabled {
        cursor: no-drop;
      }
    }
  }
}
.mb16 {
  margin-bottom: 16px;
}
.collection-rules-cls {
  /deep/ .bk-table-row-last td {
    border-bottom: none !important;
  }
}
.hide-path-cls {
  /deep/ .bk-label {
    display: none;
  }
}
</style>
<style>
.delete-collection-rule .bk-info-box .bk-dialog-content .bk-dialog-sub-header.has-sub {
  padding: 0 10px 20px 10px;
}
</style>
