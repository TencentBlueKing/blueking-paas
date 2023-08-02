<template>
  <div class="env-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-env-loading"
      class="middle"
    >
      <section v-show="!isLoading">
        <bk-alert type="info">
          <span slot="title">
            {{ $t('环境变量可以用来改变应用在不同环境下的行为；除自定义环境变量外，平台也会写入内置环境变量。') }}
            <span
              class="built-in-env"
              @click="handleShoEnvDialog"
            >{{ $t('查看内置环境变量') }}</span>
          </span>
        </bk-alert>
        <div class="flex-row align-items-center justify-content-between mt20">
          <div>
            <bk-button
              :theme="'default'"
              :outline="true"
              class="mr10"
              @click.stop.prevent="addEnvData"
            >
              {{ $t('批量导入') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              :outline="true"
              @click.stop.prevent="addEnvData"
            >
              {{ $t('批量导出') }}
            </bk-button>
          </div>
          <div>
            <bk-button
              v-if="!isPageEdit"
              class="fr"
              theme="primary"
              title="编辑"
              :outline="true"
              @click="handleEditClick">
              {{ $t('编辑') }}
            </bk-button>
          </div>
        </div>
        <bk-table
          v-bkloading="{ isLoading: isTableLoading }"
          :data="envVarList"
          v-if="envVarList.length"
          class="table-cls mt20">
          <bk-table-column :label="$t('Key')" class-name="table-colum-module-cls" sortable>
            <template slot-scope="{ row, $index }">
              <div v-if="isPageEdit" class="table-colum-cls">
                <bk-form
                  :label-width="0" form-type="inline" :ref="`envRefName${$index}`"
                  class="env-from-cls" :model="row">
                  <bk-form-item :required="true" :property="'name'" :rules="rules.name">
                    <bk-input
                      v-model="row.name" class="env-input-cls"
                      @enter="handleInputEvent(row, $index)"
                      @blur="handleInputEvent(row, $index)">
                    </bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.name }}</div>
            </template>
          </bk-table-column>

          <bk-table-column :label="$t('Value')" class-name="table-colum-module-cls">
            <template slot-scope="{ row }">
              <div v-if="isPageEdit">
                <bk-form
                  :label-width="0" form-type="inline" :ref="`envRefValue`"
                  class="env-from-cls" :model="row">
                  <bk-form-item :required="true" :property="'value'" :rules="rules.value">
                    <bk-input v-model="row.value" class="env-input-cls">
                    </bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.value }}</div>
            </template>
          </bk-table-column>

          <bk-table-column :label="$t('生效环境')" class-name="table-colum-module-cls">
            <template slot-scope="{ row }">
              <div v-if="isPageEdit">
                <bk-form
                  form-type="inline"
                  class="env-from-cls">
                  <bk-form-item :required="true">
                    <bk-select
                      v-model="row.envName"
                      :placeholder="$t('请选择')"
                      :clearable="false"
                      style="width: 200px"
                      @change="handleEnvChange(row)"
                    >
                      <bk-option
                        v-for="(option, optionIndex) in envSelectList"
                        :id="option.id"
                        :key="optionIndex"
                        :name="option.text"
                      />
                    </bk-select>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.envName }}</div>
            </template>
          </bk-table-column>

          <bk-table-column :label="$t('描述')" class-name="table-colum-module-cls">
            <template slot-scope="{ row }">
              <div v-if="isPageEdit">
                <bk-form
                  form-type="inline" :ref="`envRefDescription`"
                  class="env-from-cls">
                  <bk-form-item :required="true" :property="'description'" :rules="rules.description">
                    <bk-input v-model="row.description" class="env-input-cls">
                    </bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.description || '--' }}</div>
            </template>
          </bk-table-column>

          <bk-table-column :label="$t('操作')" width="200" class-name="table-colum-module-cls" v-if="isPageEdit">
            <template slot-scope="{ $index }">
              <div v-if="isPageEdit" class="env-table-icon">
                <i class="icon paasng-icon paasng-plus-circle-shape" @click="handleEnvTableListData('add', $index)"></i>
                <i
                  class="icon paasng-icon paasng-minus-circle-shape pl20"
                  v-if="envVarList.length > 1"
                  @click="handleEnvTableListData('reduce', $index)"></i>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
        <div
          v-else
          class="ps-no-result"
        >
          <table-empty empty />
        </div>
      </section>
    </paas-content-loader>

    <bk-sideslider
      :is-show.sync="envSidesliderConf.visiable"
      :width="800"
      :title="$t('内置环境变量')"
      :quick-close="true"
      @shown="showEnvVariable"
    >
      <div
        slot="content"
        v-bkloading="{ isLoading: envLoading, zIndex: 10 }"
        class="slider-env-content"
      >
        <div v-if="basicInfo.length">
          <p class="env-title mb10">
            {{ $t('应用基本信息') }}
          </p>
          <div ref="basicInfoWrapper">
            <p
              v-for="item in basicInfo"
              :key="item.label"
              class="env-item"
            >
              <span
                ref="basicText"
                v-bk-tooltips="{ content: `${item.label}: ${item.value}`, disabled: item.isTips }"
              >{{ item.label }}: {{ item.value }}</span>
            </p>
          </div>
        </div>
        <div v-if="appRuntimeInfo.length">
          <p class="env-title mt15 mb10">
            {{ $t('应用运行时信息') }}
          </p>
          <div ref="appRuntimeInfoWrapper">
            <p
              v-for="item in appRuntimeInfo"
              :key="item.label"
              class="env-item"
            >
              <span
                ref="appRuntimeText"
                v-bk-tooltips="{ content: `${item.label}: ${item.value}`, disabled: item.isTips }"
              >{{ item.label }}: {{ item.value }}</span>
            </p>
          </div>
        </div>
        <div v-if="bkPlatformInfo.length">
          <p class="env-title mt15 mb10">
            {{ $t('蓝鲸体系内平台地址') }}
          </p>
          <div ref="bkPlatformInfoWrapper">
            <p
              v-for="item in bkPlatformInfo"
              :key="item.label"
              class="env-item"
            >
              <span
                ref="bkPlatformText"
                v-bk-tooltips="{ content: `${item.label}: ${item.value}`, disabled: item.isTips }"
              >{{ item.label }}={{ item.value }}</span>
            </p>
          </div>
        </div>
        <p class="reminder">
          {{ $t('增强服务也会写入相关的环境变量，可在增强服务的“实例详情”页面的“配置信息”中查看') }}
        </p>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>import _ from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import i18n from '@/language/i18n.js';

export default {
  components: {
  },
  mixins: [appBaseMixin],
  props: {
    cloudAppData: {
      type: Object,
      default: {},
    },
  },
  data() {
    return {
      curItem: {},
      envVarList: [],
      runtimeImageList: [],
      rules: {
        name: [
          {
            required: true,
            message: i18n.t('NAME是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^[-._a-zA-Z][-._a-zA-Z0-9]*$/,
            message: i18n.t('环境变量名称必须由字母字符、数字、下划线（_）、连接符（-）、点（.）组成，并且不得以数字开头（例如“my.env-name”或“MY_ENV.NAME”, 或 “MyEnvName1”）'),
            trigger: 'blur',
          },
          {
            validator: () => {
              const flag = this.envVarList.filter(item => item.name === this.curItem.name
              && item.envName === this.curItem.envName);
              if (flag.length <= 1) {   // 如果符合要求需要清除错误
                this.envVarList.forEach((e, i) => {
                  this.$refs[`envRefName${i}`].clearError();
                });
              }
              return flag.length <= 1;
            },
            message: () => this.$t(`该环境下名称为 ${this.curItem.name} 的变量已经存在，不能重复添加。`),
            trigger: 'blur',
          },
        ],
        value: [
          {
            required: true,
            message: i18n.t('VALUE是必填项'),
            trigger: 'blur',
          },
          {
            max: 2048,
            message: i18n.t('不能超过2048个字符'),
            trigger: 'blur',
          },
        ],
        description: [
          {
            validator: (value) => {
              if (value === '') {
                return true;
              }
              return value.trim().length <= 200;
            },
            message: i18n.t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
      editRowList: [],
      isLoading: true,
      isVarLoading: true,

      envSidesliderConf: {
        visiable: false,
      },
      basicInfo: [],
      appRuntimeInfo: [],
      bkPlatformInfo: [],
      loadingConf: {
        basicLoading: false,
        appRuntimeLoading: false,
        bkPlatformLoading: false,
      },
      envSelectList: [
        { id: '_global_', text: this.$t('所有环境') },
        { id: 'stag', text: this.$t('预发布环境') },
        { id: 'prod', text: this.$t('生产环境') },
      ],
      isTableLoading: true,
      localCloudAppData: {},
    };
  },
  computed: {
    envLoading() {
      return this.loadingConf.basicLoading || this.loadingConf.appRuntimeLoading || this.loadingConf.bkPlatformLoading;
    },

    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit;
    },
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData = _.cloneDeep(val);
          this.envVarList = [...val.spec.configuration.env, ...val.spec.envOverlay.envVariables];
          this.envLocalVarList = _.cloneDeep(this.envVarList);

          setTimeout(() => {
            this.isLoading = false;
            this.isTableLoading = false;
          }, 500);
        }
      },
      immediate: true,
    },

    envVarList: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData.spec.envOverlay.envVariables = [...val];
          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        }
      },
      deep: true,
    },
  },
  created() {
  },
  methods: {
    init() {
      this.isLoading = true;
      this.getAllImages();
    },
    async getAllImages() {
      try {
        const res = await this.$store.dispatch('envVar/getAllImages', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });

        if (res.results) {
          res.results.forEach((item) => {
            item.name = `${item.slugbuilder.display_name || item.image} (${item.slugbuilder.description || '--'})`;

            item.buildpacks.forEach((item) => {
              item.name = `${item.display_name || item.name} (${item.description || '--'})`;
            });
          });
          this.runtimeImageList = res.results;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },
    // 处理input事件
    handleInputEvent(rowItem, rowIndex) {
      this.curItem = rowItem;
      console.log('this.curItem', this.curItem, rowIndex);
    },
    addEnvData() {
      const isAdd = this.envVarList.find(item => item.isAdd);
      if (isAdd) {
        return;
      }
      this.envVarList.push({
        name: '',
        value: '',
        envName: this.curStage || '_global_',
        isAdd: true,
      });
      this.editRowList.push(this.envVarList.length - 1);
    },

    async formDataValidate() {
      console.log('this.$refs.envRefName', this.$refs.envRefName);
      // 提交时需要检验,拿到需要检验的数据下标
      const flag = this.envVarList.reduce((p, v, i) => {
        if (v.name === this.curItem.name && v.envName === this.curItem.envName) {
          p.push({ ...v, i });
        }
        return p;
      }, []);
      if (flag.length > 1) {
        flag.forEach(async (e) => {
          try {
            await this.$refs[`envRefName${e.i}`].validate();
            return true;
          } catch (error) {
            return false;
          }
        });
      } else {
        return true;
      }
    },

    handleShoEnvDialog() {
      this.envSidesliderConf.visiable = true;
    },

    showEnvVariable() {
      this.getBasicInfo();
      this.getAppRuntimeInfo();
      this.getBkPlatformInfo();
    },

    async getBasicInfo() {
      try {
        this.loadingConf.basicLoading = true;
        const data = await this.$store.dispatch('envVar/getBasicInfo', { appCode: this.appCode });
        this.basicInfo = this.convertArray(data);
        this.$nextTick(() => {
          this.contrastTextWitch('basicInfoWrapper', 'basicText', this.basicInfo);
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.loadingConf.basicLoading = false;
      }
    },

    async getAppRuntimeInfo() {
      try {
        this.loadingConf.appRuntimeLoading = true;
        const data = await this.$store.dispatch('envVar/getAppRuntimeInfo', { appCode: this.appCode });
        this.appRuntimeInfo = this.convertArray(data);
        this.$nextTick(() => {
          this.contrastTextWitch('appRuntimeInfoWrapper', 'appRuntimeText', this.appRuntimeInfo);
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.loadingConf.appRuntimeLoading = false;
      }
    },

    async getBkPlatformInfo() {
      try {
        this.loadingConf.bkPlatformLoading = true;
        const data = await this.$store.dispatch('envVar/getBkPlatformInfo', { appCode: this.appCode });
        this.bkPlatformInfo = this.convertArray(data);
        this.$nextTick(() => {
          this.contrastTextWitch('bkPlatformInfoWrapper', 'bkPlatformText', this.bkPlatformInfo);
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.loadingConf.bkPlatformLoading = false;
        }, 300);
      }
    },

    // 数据转换成数组
    convertArray(data) {
      const list = Object.keys(data).reduce((p, key) => {
        p.push({
          label: key,
          value: data[key],
          isTips: true,
        });
        return p;
      }, []);
      return list;
    },

    // 文字溢出显示tooltips
    contrastTextWitch(parentRef, childRef, data) {
      const containerWitch = this.$refs[parentRef].offsetWidth;
      this.$refs[childRef].forEach((item, index) => {
        if (item.offsetWidth > containerWitch) {
          this.$set(data[index], 'isTips', false);
        }
      });
    },

    handleSort() {
    },

    // 首字母排序
    alphabeticalOrder(targetArr) {
      targetArr.sort((a, b) => {
        const textA = a.name.toUpperCase();
        const textB = b.name.toUpperCase();
        return (textA < textB) ? -1 : (textA > textB) ? 1 : 0;
      });
    },

    // 编辑页面
    handleEditClick() {
      if (!this.envVarList.length) {
        this.envVarList.push({
          name: '',
          value: '',
          envName: 'stag',
          isAdd: true,
        });
      }
      this.$store.commit('cloudApi/updatePageEdit', true);
    },

    // 新增一条数据
    handleEnvTableListData(v, i) {
      if (v === 'add') {
        this.envVarList.push({
          name: '',
          value: '',
          envName: 'stag',
          isAdd: true,
        });
      } else {
        this.envVarList.splice(i, 1);
      }
      this.localCloudAppData.spec.envOverlay.envVariables = [...this.envVarList];
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
    },

    // 选中环境
    handleEnvChange(curItem) {
      this.curItem = curItem;
      const flag = this.envVarList.filter(item => item.name === this.curItem.name
              && item.envName === this.curItem.envName);
      if (flag.length <= 1) {   // 如果符合要求需要清除错误
        this.envVarList.forEach((e, i) => {
          this.$refs[`envRefName${i}`].clearError();
        });
      }
    },
  },
};
</script>

  <style media="screen">
      .query-button {
          width: auto;
          padding-right: 30px;
      }
  </style>

  <style lang="scss">
      .ps-table-default {
          .bk-form-item {
              .bk-form-content {
                  width: 100%;
                  float: none !important;
                  display: block !important;
              }
          }
      }
  </style>

  <style lang="scss" scoped>

      .env-container{
          padding: 0 20px 20px;
          min-height: 200px;
      }
      .variable-instruction {
          font-size: 14px;
          color: #7b7d8a;
          padding: 15px 30px;
          line-height: 28px;
          border-bottom: 1px solid #eaeeee;
      }

      .paas-env-var-upload-dialog {
          .header {
              font-size: 24px;
              color: #313238;
          }
          .title {
              max-width: 150px;
              margin: 0;
              display: inline-block;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              vertical-align: bottom;
          }
          .download-tips {
              display: flex;
              justify-content: space-between;
              padding: 0 10px;
              line-height: 40px;
              background: #fefaf2;
              font-size: 12px;
              color: #ffb400;
          }
      }

      a.is-disabled {
          color: #dcdee5 !important;
          cursor: not-allowed !important;
          &:hover {
              background: #fff !important;
          }
      }

      .upload-content {
          margin-top: 15px;
          text-align: center;
          .file-icon {
              font-size: 40px;
              color: #dae1e8;
          }
          .cur-upload-file {
              display: inline-block;
              line-height: 1;
              font-size: 12px;
              color: #3a84ff;
              border-bottom: 1px solid #3a84ff;
          }
          .file-error-tips {
              display: inline-block;
              line-height: 1;
              font-size: 12px;
              color: #ff4d4d;
          }
      }

      .ps-table-width-overflowed {
          width: 100%;
          margin-left: 0;

          td {
              border-bottom: 0;
              padding: 15px 0 0 0;
          }

          .desc-form-content {
              display: inline-block;
              padding: 0 10px;
              width: 100%;
              height: 32px;
              border: 1px solid #dcdee5;
              border-radius: 2px;
              text-align: left;
              font-size: 12px;
              color: #63656e;
              overflow: hidden;
              background-color: #fafbfd;
              vertical-align: middle;
              cursor: default;
          }
          .bk-inline-form {
              display: flex;
          }
      }

      .variable-main {
          border-bottom: 0;

          h3 {
              line-height: 1;
              padding: 10px 0;
          }

          .ps-alert-content {
              color: #666;
          }
      }

      .variable-input {
          margin-right: 10px;

          input {
              height: 36px;
          }
      }

      .variable-select {
          margin-right: 10px;
      }

      .variable-operation {
          font-size: 0;

          button {
              width: 72px;
              line-height: 18px;
              -webkit-box-sizing: border-box;
              -moz-box-sizing: border-box;
              -ms-box-sizing: border-box;
              box-sizing: border-box;
              -webkit-transition: 0s all;
              -moz-transition: 0s all;
              -ms-transition: 0s all;
              transition: 0s all;
          }

          a {
              &.paasng-delete {
                  font-size: 16px;
              }

              &.paasng-check-1 {
                  font-size: 15px;
              }
          }
      }

      .middle {
          > p {
              line-height: 46px;
          }
      }

      .variabletext {
          width: 100%;
          box-sizing: border-box;
          line-height: 30px;
          height: 34px;
      }

      .filter-list {
          position: relative;
          font-size: 0;
          letter-spacing: -5px;
          margin: 25px 0 5px 0;

          .label {
              position: relative;
              display: inline-block;
              top: 4px;
              letter-spacing: 0;
              font-size: 14px;
          }

          .reset-button {
              position: relative;
              top: 4px;
              padding-left: 10px;
          }

          .env-export-wrapper {
              position: absolute;
              right: 80px;
          }

          .env-sort-wrapper {
              position: absolute;
              left: 410px;
              .sort-icon {
                  position: absolute;
                  // width: 26px;
                  font-size: 26px;
                  left: 5px;
                  top: 2px;
              }
              .text {
                  padding-left: 15px;
              }
              a.active {
                  background-color: #eaf3ff;
                  color: #3a84ff;
              }
          }

          a {
              letter-spacing: 0;
              font-size: 14px;
              padding: 8px 20px;
              line-height: 14px;
              margin-right: 10px;

              &.ps-btn {
                  border: 1px solid #ccc;
                  color: #999;

                  &:hover {
                      border: 1px solid #3c96ff;
                      color: #3c96ff;
                  }
              }

              &.ps-btn-primary {
                  background: #3c96ff;
                  border: 1px solid #3A84FF;
                  color: #FFF;

                  &:hover {
                      color: #FFF;
                  }
              }
          }

          .env-sort-btn {
              position: absolute;
              right: 0;
              .sort-icon {
                  position: absolute;
                  font-size: 26px;
                  left: 5px;
                  top: 2px;
              }
              .text {
                  padding-left: 15px;
              }
              &:hover {
                  color: #3a84ff;
                  border-color: #3a84ff;
              }
          }
      }

      .selectize-control * {
          cursor: pointer;
      }

      .editingEnvRow {
          color: #3a84ff;
      }

      .disabledButton:hover {
          cursor: pointer;
          color: #666;
          background: #fafafa;
      }

      .releasebg {
          padding: 0 20px 20px 20px;
          position: relative;
          border: solid 1px #e5e5e5;

          &-compact {
              padding-bottom: 5px;
          }

          .warningIcon {
              position: absolute;
              left: 20px;
              top: 28px;
              width: 24px;
              height: 24px;

              img {
                  width: 100%;
              }
          }

          .warningText {
              margin-left: 10px;
              padding-bottom: 20px;
              position: relative;
              top: 0;
              right: 0;

              h2 {
                  padding-left: 0;
              }

              &-compact {
                  padding-bottom: 5px;
              }
          }
      }

      .ps-btn-xs {
          line-height: 34px;
      }

      .ps-form-control[readonly] {
          background-color: #fafafa;
      }

      .middle h4 {
          padding-top: 0;
      }

      .ps-alert h4 {
          margin: 0;
      }

      .ps-btn-dropdown,
      .ps-btn-l {
          box-sizing: border-box;
          height: 36px;
      }

      .form-grid {
          display: flex;
      }

      .builder-item {
          padding: 0 10px;
          line-height: 20px;
          position: relative;

          &:before {
              content: '';
              font-size: 12px;
              position: absolute;
              left: 0;
              top: 8px;
              width: 3px;
              height: 3px;
              display: inline-block;
              background: #656565;
          }
      }

      .export-by-module-tips {
          padding: 4px 0 0 37px;
          line-height: 32px;
          color: #979ba5;
          font-size: 12px;
      }

      .paas-env-var-export {
          display: flex;
          justify-content: flex-start;
          .title {
              line-height: 30px;
          }
      }

      .link-a:hover {
          color: #699df4;
      }

      .img-exception {
          width: 300px;
      }
      .text-exception {
          color: #979ba5;
          font-size: 14px;
          text-align: center;
          margin-top: 14px;
      }
      .built-in-env {
          text-decoration: none !important;
          color: #699df4;

          &:hover {
              cursor: pointer;
          }
      }

      .slider-env-content {
          padding: 30px;
          min-height: calc(100vh - 50px);
      }
      .env-title {
          font-size: 14px;
          font-weight: bold;
          margin-bottom: 5px;
          color: #313238;
          line-height: 1;
      }

      .env-item {
          font-size: 12px;
          line-height: 24px;
          overflow: hidden;
          white-space: nowrap;
          text-overflow: ellipsis;
      }

      .reminder {
          margin-top: 15px;
          line-height: 24px;
          font-size: 13px;
          color: #ff9c01;
      }

      .desc-env {
          font-size: 12px;
          color: #979BA5;
          margin-bottom: 10px;
      }

      .env-table-icon{
        color: #C4C6CC;
        font-size: 14px;
        .icon{
          cursor: pointer;
        }
      }

      .env-from-cls{
        width: 100%;
        /deep/ .bk-form-item{
          width: 100%;
          .bk-form-content{
            width: 100%;
          }
        }
      }
    .env-input-cls{
      /deep/ .bk-form-input{
        width: 90%;
      }
    }
  </style>

