<template>
  <div class="env-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-env-loading"
      :is-transition="false"
      :offset-top="0"
      :offset-left="0"
      class="middle"
    >
      <section v-show="!isLoading">
        <bk-alert type="info">
          <span slot="title">
            {{ $t('环境变量可以用来改变应用在不同环境下的行为；除自定义环境变量外，平台也会写入内置环境变量。') }}
            <span
              class="built-in-env"
              @click="handleShoEnvDialog"
            >
              {{ $t('查看内置环境变量') }}
            </span>
          </span>
        </bk-alert>
        <div class="flex-row align-items-center justify-content-between mt20">
          <div class="left-filter">
            <ul class="filter-action-list" v-if="!isBatchEdit">
              <li
                @click="handleFilterEnv('all')"
                :class="{ 'active': activeEnvValue === 'all' }"
              >{{ $t('全部') }}</li>
              <li
                v-for="item in envSelectList"
                :key="item.value"
                @click="handleFilterEnv(item.value)"
                :class="{ 'active': activeEnvValue === item.value }"
              >{{ item.text }}</li>
            </ul>
          </div>
          <div class="right flex-row align-items-center">
            <bk-button
              v-if="!isBatchEdit"
              :theme="'default'"
              class="export-btn-cls mr10"
              :outline="true"
              @click="handleEditClick"
            >
              {{ $t('批量编辑') }}
            </bk-button>
            <bk-dropdown-menu
              ref="largeDropdown"
              trigger="click"
              ext-cls="env-export-wrapper"
            >
              <bk-button
                slot="dropdown-trigger"
                class="mr10"
              >
                <i class="paasng-icon paasng-upload mr6"></i>
                {{ $t('导入') }}
              </bk-button>
              <ul
                slot="dropdown-content"
                class="bk-dropdown-list"
              >
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    :class="addedModuleList.length < 1 || !canModifyEnvVariable ? 'is-disabled' : ''"
                    @click="handleCloneFromModule"
                  >
                    {{ $t('从模块导入') }}
                  </a>
                </li>
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    :class="!canModifyEnvVariable ? 'is-disabled' : ''"
                    @click="handleImportFromFile"
                  >
                    {{ $t('从文件导入') }}
                  </a>
                </li>
              </ul>
            </bk-dropdown-menu>
            <bk-button
              :theme="'default'"
              :outline="true"
              class="export-btn-cls"
              @click="handleExportToFile"
            >
              <i class="paasng-icon paasng-import mr6"></i>
              {{ $t('导出') }}
            </bk-button>
          </div>
        </div>
        <bk-table
          v-bkloading="{ isLoading: isTableLoading }"
          :data="envVarList"
          class="variable-table-cls mt20"
        >
          <!-- 新建环境变量 -->
          <template slot="append" v-if="!isPageEdit">
            <div class="add-wrapper">
              <span class="add-single-variable" @click.self="handleAddSingleVariable()">
                <i class="paasng-icon paasng-plus-thick" />
                {{ $t('新增环境变量') }}
              </span>
            </div>
          </template>
          <bk-table-column
            :render-header="handleRenderHander"
            class-name="table-colum-module-cls"
            :sortable="!isPageEdit"
          >
            <template slot-scope="{ row, $index }">
              <div
                v-if="isPageEdit || row.isEdit"
                class="table-colum-cls"
              >
                <bk-form
                  :label-width="0"
                  form-type="inline"
                  :ref="`envRefKey${$index}`"
                  class="env-from-cls"
                  :model="row"
                >
                  <bk-form-item
                    :required="true"
                    :property="'key'"
                    :rules="rules.key"
                  >
                    <bk-input
                      v-model="row.key"
                      class="env-input-cls"
                      @enter="handleInputEvent(row, $index)"
                      @blur="handleInputEvent(row, $index)"
                    ></bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.key }}</div>
            </template>
          </bk-table-column>

          <bk-table-column
            :render-header="handleRenderHander"
            class-name="table-colum-module-cls"
          >
            <template slot-scope="{ row, $index }">
              <div v-if="isPageEdit || row.isEdit">
                <bk-form
                  :label-width="0"
                  form-type="inline"
                  :ref="`envRefValue${$index}`"
                  class="env-from-cls"
                  :model="row"
                >
                  <bk-form-item
                    :required="true"
                    :property="'value'"
                    :rules="rules.value"
                  >
                    <bk-input
                      v-model="row.value"
                      @enter="handleInputEvent(row, $index)"
                      @blur="handleInputEvent(row, $index)"
                      class="env-input-cls"
                    ></bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.value }}</div>
            </template>
          </bk-table-column>

          <bk-table-column
            :render-header="handleRenderHander"
            class-name="table-colum-module-cls"
            prop="environment_name"
          >
            <template slot-scope="{ row }">
              <div v-if="isPageEdit || row.isEdit">
                <bk-form
                  form-type="inline"
                  class="env-from-cls"
                >
                  <bk-form-item :required="true">
                    <bk-select
                      v-model="row.environment_name"
                      :placeholder="$t('请选择')"
                      :clearable="false"
                      @change="handleEnvChange(row)"
                    >
                      <bk-option
                        v-for="(option, optionIndex) in envSelectList"
                        :id="option.value"
                        :key="optionIndex"
                        :name="option.text"
                      />
                    </bk-select>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ envEnums[row.environment_name] || $t('所有环境') }}</div>
            </template>
          </bk-table-column>

          <bk-table-column
            :label="$t('描述')"
            class-name="table-colum-module-cls"
          >
            <template slot-scope="{ row }">
              <div v-if="isPageEdit || row.isEdit">
                <bk-form
                  form-type="inline"
                  :ref="`envRefDescription`"
                  class="env-from-cls"
                >
                  <bk-form-item
                    :required="true"
                    :property="'description'"
                    :rules="rules.description"
                  >
                    <bk-input
                      v-model="row.description"
                      class="env-input-cls"
                    ></bk-input>
                  </bk-form-item>
                </bk-form>
              </div>
              <div v-else>{{ row.description || '--' }}</div>
            </template>
          </bk-table-column>

          <bk-table-column
            :label="$t('操作')"
            width="100"
            class-name="table-colum-module-cls"
          >
            <template slot-scope="{ $index, row }">
              <!-- 批量编辑 -->
              <div
                v-if="isPageEdit"
                class="env-table-icon"
              >
                <i
                  class="icon paasng-icon paasng-plus-circle-shape"
                  @click="handleEnvTableListData('add', $index)"
                ></i>
                <i
                  class="icon paasng-icon paasng-minus-circle-shape pl20"
                  v-if="envVarList.length > 1"
                  @click="handleEnvTableListData('reduce', $index)"
                ></i>
              </div>
              <!-- 单个编辑 -->
              <div v-else>
                <template v-if="!row.isEdit">
                  <bk-button :text="true" title="primary" class="mr10" @click="handleSingleEdit($index)">
                    {{ $t('编辑') }}
                  </bk-button>
                  <bk-popconfirm
                    trigger="click"
                    :ext-cls="'asadsadsads'"
                    width="288"
                    @confirm="handleSingleDelete(row)"
                  >
                    <div slot="content">
                      <div class="demo-custom mb10">
                        <div class="content-text">{{ $t('确认删除该环境变量？') }}</div>
                      </div>
                    </div>
                    <bk-button :text="true" title="primary">
                      {{ $t('删除') }}
                    </bk-button>
                  </bk-popconfirm>
                </template>
                <template v-else>
                  <bk-button :text="true" title="primary" class="mr10" @click="handleSingleSave($index)">
                    {{ $t('保存') }}
                  </bk-button>
                  <bk-button :text="true" title="primary" @click="handleSingleCancel($index)">
                    {{ $t('取消') }}
                  </bk-button>
                </template>
              </div>
            </template>
          </bk-table-column>
        </bk-table>

        <div
          class="env-btn-wrapper"
          v-if="isPageEdit && isComponentBtn"
        >
          <bk-button
            class="pl20 pr20"
            :theme="'primary'"
            @click="saveEnvData"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            class="pl20 pr20 ml20"
            @click="$emit('cancel')"
          >
            {{ $t('取消') }}
          </bk-button>
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
              >
                {{ item.label }}: {{ item.value }}
              </span>
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
              >
                {{ item.label }}: {{ item.value }}
              </span>
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
              >
                {{ item.label }}={{ item.value }}
              </span>
            </p>
          </div>
        </div>
        <p class="reminder">
          {{ $t('增强服务也会写入相关的环境变量，可在增强服务的“实例详情”页面的“配置信息”中查看') }}
        </p>
      </div>
    </bk-sideslider>

    <bk-dialog
      v-model="exportDialog.visiable"
      :title="$t('从其它模块导入环境变量')"
      :header-position="exportDialog.headerPosition"
      :width="exportDialog.width"
      @after-leave="handleAfterLeave"
    >
      <div>
        <div class="paas-env-var-export">
          <label class="title">{{ $t('模块：') }}</label>
          <bk-select
            v-model="moduleValue"
            :disabled="false"
            :clearable="false"
            searchable
            style="flex: 0 0 390px"
            @selected="handleModuleSelected"
          >
            <bk-option
              v-for="option in addedModuleList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </div>
        <div
          v-bkloading="{ isLoading: exportDialog.isLoading, opacity: 1 }"
          class="export-by-module-tips"
        >
          <p
            v-if="exportDialog.count"
            style="line-height: 20px"
          >
            【{{ curSelectModuleName }}】 {{ $t('模块共有') }}
            {{ exportDialog.count }} {{ $t('个环境变量，将增量更新到当前') }} 【{{ curModuleId }} 】{{ $t('模块') }}
          </p>
          <p v-else>【{{ curSelectModuleName }}】 {{ $t('模块暂无环境变量，请选择其它模块') }}</p>
        </div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          class="mr10"
          :disabled="exportDialog.count < 1"
          :loading="exportDialog.loading"
          @click="handleExportConfirm"
        >
          {{ $t('确定导入') }}
        </bk-button>
        <bk-button @click="handleExportCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="importFileDialog.visiable"
      :header-position="importFileDialog.headerPosition"
      :loading="importFileDialog.loading"
      :width="importFileDialog.width"
      :ok-text="$t('确定导入')"
      ext-cls="paas-env-var-upload-dialog"
      @after-leave="handleImportFileLeave"
    >
      <div
        slot="header"
        class="header"
      >
        {{ $t('从文件导入环境变量到') }}【<span
          class="title"
          :title="curModuleId"
        >{{ curModuleId }}</span> 】{{ $t('模块') }}
      </div>
      <div>
        <div class="download-tips">
          <span>
            <i class="paasng-icon paasng-exclamation-circle" />
            {{ $t('请先下载模板，按格式修改后点击“选择文件”批量导入') }}
          </span>
          <bk-button
            text
            theme="primary"
            size="small"
            style="line-height: 40px"
            @click="handleDownloadTemplate"
          >
            {{ $t('下载模板') }}
          </bk-button>
        </div>
        <div class="upload-content">
          <p><i class="paasng-icon paasng-file-fill file-icon" /></p>
          <p>
            <bk-button
              text
              theme="primary"
              ext-cls="env-var-upload-btn-cls"
              @click="handleTriggerUpload"
            >
              {{ $t('选择文件') }}
            </bk-button>
          </p>
          <p
            v-if="curFile.name"
            class="cur-upload-file"
          >
            {{ $t('已选择文件：') }} {{ curFile.name }}
          </p>
          <p
            v-if="isFileTypeError"
            class="file-error-tips"
          >
            {{ $t('请选择yaml文件') }}
          </p>
        </div>

        <input
          ref="upload"
          type="file"
          style="position: absolute; width: 0; height: 0"
          @change="handleStartUpload"
        />
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          class="mr10"
          :loading="importFileDialog.loading"
          :disabled="!curFile.name"
          @click="handleImportFileConfirm"
        >
          {{ $t('确定导入') }}
        </bk-button>
        <bk-button @click="handleImportFileCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>import _ from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import i18n from '@/language/i18n.js';
import { ENV_ENUM } from '@/common/constants';

export default {
  components: {},
  mixins: [appBaseMixin],
  props: {
    // 组件内部按钮操作
    isComponentBtn: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      curItem: {},
      envVarList: [],
      runtimeImageList: [],
      rules: {
        key: [
          {
            required: true,
            message: this.$t('KEY是必填项'),
            trigger: 'blur',
          },
          {
            max: 64,
            message: this.$t('不能超过64个字符'),
            trigger: 'blur',
          },
          {
            regex: /^[A-Z][A-Z0-9_]*$/,
            message: this.$t('只能以大写字母开头，仅包含大写字母、数字与下划线'),
            trigger: 'blur',
          },
          {
            validator: () => {
              const flag = this.envVarList.filter(item => item.key === this.curItem.key
              && item.environment_name === this.curItem.environment_name);
              if (flag.length <= 1) {
                // 如果符合要求需要清除错误
                this.envVarList.forEach((e, i) => {
                  this.$refs[`envRefKey${i}`] && this.$refs[`envRefKey${i}`].clearError();
                });
              }
              return flag.length <= 1;
            },
            message: () => this.$t(`该环境下名称为 ${this.curItem.key} 的变量已经存在，不能重复添加。`),
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
              if (!value) {
                return true;
              }
              return value.trim().length <= 200;
            },
            message: i18n.t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
      isLoading: true,
      isTableLoading: true,

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
        { value: '_global_', text: this.$t('所有环境') },
        { value: 'stag', text: this.$t('预发布环境') },
        { value: 'prod', text: this.$t('生产环境') },
      ],
      curSortKey: '-created',
      exportDialog: {
        visiable: false,
        width: 480,
        headerPosition: 'center',
        loading: false,
        isLoading: false,
        count: 0,
      },
      importFileDialog: {
        visiable: false,
        width: 540,
        headerPosition: 'center',
        loading: false,
      },
      moduleValue: '',
      curSelectModuleName: '',
      curFile: {},
      isFileTypeError: false,
      envEnums: ENV_ENUM,
      isBatchEdit: false,
      activeEnvValue: 'all',
    };
  },
  computed: {
    envLoading() {
      return this.loadingConf.basicLoading || this.loadingConf.appRuntimeLoading || this.loadingConf.bkPlatformLoading;
    },

    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit;
    },

    canModifyEnvVariable() {
      return this.curAppInfo && this.curAppInfo.feature.MODIFY_ENVIRONMENT_VARIABLE;
    },

    addedModuleList() {
      return this.curAppModuleList.filter(item => item.name !== this.curModuleId);
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.isLoading = true;
      this.getEnvVarList();
    },
    getEnvVarList() {
      this.isTableLoading = true;
      this.$http.get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/?order_by=${this.curSortKey}`).then((response) => {
        this.envVarList = [...response];
        // 添加自定义属性
        this.envVarList.forEach((v) => {
          this.$set(v, 'isEdit', false);
        });
        this.envLocalVarList = _.cloneDeep(this.envVarList);
        this.handleFilterEnv(this.activeEnvValue);
      }, (errRes) => {
        const errorMsg = errRes.message;
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
        });
      })
        .finally(() => {
          this.isTableLoading = false;
          this.isLoading = false;
        });
    },
    // 处理input事件
    handleInputEvent(rowItem) {
      this.curItem = rowItem;
    },

    async saveEnvData() {
      let validate = true;
      // 提交时需要检验,拿到需要检验的数据下标
      const flag = this.envVarList.reduce((p, v, i) => {
        if (v.key === this.curItem.key && v.environment_name === this.curItem.environment_name) {
          p.push({ ...v, i });
        }
        return p;
      }, []);
      // 仅一条数据也可删除
      if (this.envVarList.length === 0) {
        this.save();
        return;
      }
      if (flag.length) {
        // 有数据时
        for (let index = 0; index < flag.length; index++) {
          try {
            await this.$refs[`envRefKey${flag[index].i}`].validate();
            await this.$refs[`envRefValue${flag[index].i}`].validate();
          } catch (error) {
            validate = false;
            break;
          }
        }
      } else {
        // 新增第一条数据时
        try {
          await this.$refs.envRefKey0.validate();
          await this.$refs.envRefValue0.validate();
        } catch (error) {
          validate = false;
        }
      }
      if (validate) {
        // 通过检验才可以保存
        this.save();
      }
    },

    // 单条环境变量校验
    async singleValidate(i, type) {
      try {
        await this.$refs[`envRefKey${i}`].validate();
        await this.$refs[`envRefValue${i}`].validate();
        const data = _.cloneDeep(this.envVarList[i]);
        // 单条新建编辑操作
        type === 'add' ? this.createdEnvVariable(data, i) : this.updateEnvVariable(data, i);
      } catch (error) {
        console.error(error);
      }
    },

    // 新增加单个环境变量
    async createdEnvVariable(data, i) {
      // 删除冗余数据
      delete data.isEdit;
      delete data.isAdd;
      try {
        await this.$store.dispatch('envVar/createdEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加环境变量成功'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加环境变量失败')}，${e.message}`,
        });
      } finally {
        this.envVarList[i].isEdit = false;
        // 更新数据
        this.getEnvVarList();
      }
    },

    // 修改加单个环境变量
    async updateEnvVariable(data, i) {
      // 删除冗余数据
      delete data.isEdit;
      try {
        await this.$store.dispatch('envVar/updateEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId: data.id,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('修改环境变量成功'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('修改环境变量失败')}，${e.message}`,
        });
      } finally {
        this.envVarList[i].isEdit = false;
        this.getEnvVarList();
      }
    },

    // 保存
    async save() {
      try {
        const params = _.cloneDeep(this.envVarList);

        // 保存环境变，无需传递 is_global
        params.forEach((v) => {
          delete v.is_global;
          delete v.isEdit;
        });

        await this.$store.dispatch('envVar/saveEnvItem', { appCode: this.appCode, moduleId: this.curModuleId, data: params });
        // 操作对应tips
        let tipsType = this.envVarList.length > this.envLocalVarList.length ? '新建' : '删除';
        if (this.envVarList.length === this.envLocalVarList.length) {
          tipsType = '修改';
        }
        this.$paasMessage({
          theme: 'success',
          message: this.$t(`${tipsType}环境变量成功`),
        });
        this.envVarList.forEach((v) => {
          this.$set(v, 'isEdit', false);
        });
        // 更新本地数据
        this.envLocalVarList = _.cloneDeep(this.envVarList);
        this.$store.commit('cloudApi/updatePageEdit', false);
      } catch (error) {
        const errorMsg = error.message;
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加环境变量失败')}，${errorMsg}`,
        });
      }
      this.isBatchEdit = false;
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

    // 编辑页面
    handleEditClick() {
      if (!this.envVarList.length) {
        this.envVarList.push({
          key: '',
          value: '',
          environment_name: 'stag',
          description: '',
        });
      }
      // 批量编辑展示所有环境变量
      this.handleFilterEnv('all');
      this.isBatchEdit = true;
      this.$store.commit('cloudApi/updatePageEdit', true);
    },

    // 新增一条数据
    handleEnvTableListData(v, i) {
      if (v === 'add') {
        this.envVarList.push({
          key: '',
          value: '',
          environment_name: 'stag',
          description: '',
          isEdit: true,
        });
      } else {
        this.envVarList.splice(i, 1);
      }
    },

    // 选中环境
    handleEnvChange(curItem) {
      this.curItem = curItem;
      const flag = this.envVarList.filter(item => item.name === this.curItem.name
      && item.envName === this.curItem.envName);
      if (flag.length <= 1) {
        // 如果符合要求需要清除错误
        this.envVarList.forEach((e, i) => {
          this.$refs[`envRefKey${i}`].clearError();
        });
      }
    },

    handleCloneFromModule() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      if (this.addedModuleList.length < 1) {
        return;
      }
      this.exportDialog.visiable = true;
      this.moduleValue = this.addedModuleList[0].id;
      this.curSelectModuleName = this.addedModuleList[0].name;
      this.handleModuleSelected('', { name: this.curSelectModuleName });
    },

    handleModuleSelected(value, { name }) {
      this.curSelectModuleName = name;
      this.exportDialog.isLoading = true;
      this.$http
        .get(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curSelectModuleName}/config_vars/?order_by=-created`)
        .then(
          (response) => {
            this.exportDialog.count = (response || []).length;
          },
          (errRes) => {
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
            });
          },
        )
        .finally(() => {
          this.exportDialog.isLoading = false;
        });
    },

    async handleExportConfirm() {
      this.exportDialog.loading = true;
      try {
        const res = await this.$store.dispatch('envVar/exportModuleEnv', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          sourceModuleName: this.curSelectModuleName,
        });
        const createNum = res.create_num;
        const overwritedNum = res.overwrited_num;
        const ignoreNum = res.ignore_num;
        this.isEdited = createNum > 0 || overwritedNum > 0;
        const message = (() => {
          const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(Boolean(ignoreNum))}`;
          let messageText = '';
          switch (numStr) {
            case '111':
              messageText = `${this.$t('导入成功，新增 ')}${createNum}${this.$t('个变量，更新')}${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '110':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量，更新')} ${overwritedNum} ${this.$t('个变量')}`;
              break;
            case '100':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量')}`;
              break;
            case '101':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '011':
              messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '010':
              messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量')}`;
              break;
            case '001':
              messageText = this.$t('所有环境变量都已在当前模块中，已全部忽略');
              break;
            default:
              messageText = `${this.$t('导入成功')}`;
          }
          return messageText;
        })();
        this.$paasMessage({
          theme: 'success',
          message,
        });
        this.handleExportCancel();
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.exportDialog.loading = false;
      }
    },
    handleExportCancel() {
      this.exportDialog.visiable = false;
    },

    handleImportFileCancel() {
      this.importFileDialog.visiable = false;
    },

    handleAfterLeave() {
      this.moduleValue = '';
      this.curSelectModuleName = '';
      this.exportDialog.count = 0;
    },

    // 从文件导入
    handleImportFromFile() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      this.importFileDialog.visiable = true;
    },

    handleExportToFile() {
      this.exportLoading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/export/?order_by=${this.curSortKey}`;
      this.$http
        .get(url)
        .then(
          (response) => {
            this.invokeBrowserDownload(response, `bk_paas3_${this.appCode}_${this.curModuleId}_env_vars.yaml`);
          },
          (errRes) => {
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
            });
          },
        )
        .finally(() => {
          this.exportLoading = false;
        });
    },

    handleImportFileLeave() {
      this.curFile = {};
      this.isFileTypeError = false;
    },

    handleDownloadTemplate() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/template/`;
      this.$http.get(url).then(
        (response) => {
          this.invokeBrowserDownload(response, 'bk_paas3_env_vars_import_template.yaml');
        },
        (errRes) => {
          const errorMsg = errRes.detail;
          this.$paasMessage({
            theme: 'error',
            message: `${this.$t('获取yaml模板失败')}，${errorMsg}`,
          });
        },
      );
    },

    handleTriggerUpload() {
      this.$refs.upload.click();
    },

    handleStartUpload(payload) {
      const files = Array.from(payload.target.files);
      const curFile = files[0];
      const fileExtension = curFile.name.substring(curFile.name.lastIndexOf('.') + 1);
      if (fileExtension !== 'yaml') {
        this.isFileTypeError = true;
        return;
      }
      this.isFileTypeError = false;
      this.curFile = curFile;
      this.$refs.upload.value = '';
    },

    handleImportFileConfirm() {
      this.importFileDialog.loading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/import/`;
      const params = new FormData();
      params.append('file', this.curFile);
      this.$http
        .post(url, params)
        .then(
          (response) => {
            const createNum = response.create_num;
            const overwritedNum = response.overwrited_num;
            const ignoreNum = response.ignore_num;
            this.isEdited = createNum > 0 || overwritedNum > 0;
            const message = (() => {
              const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(Boolean(ignoreNum))}`;
              let messageText = '';
              switch (numStr) {
                case '111':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量，更新')} ${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '110':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量，更新')} ${overwritedNum} ${this.$t('个变量')}`;
                  break;
                case '100':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量')}`;
                  break;
                case '101':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '011':
                  messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '010':
                  messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量')}`;
                  break;
                case '001':
                  messageText = this.$t('所有环境变量都已在当前模块中，已全部忽略');
                  break;
                default:
                  messageText = `${this.$t('导入成功')}`;
              }
              return messageText;
            })();
            this.$paasMessage({
              theme: 'success',
              message,
            });
            this.getEnvVarList();
          },
          (errRes) => {
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('从文件导入环境变量失败')}，${errorMsg}`,
            });
          },
        )
        .finally(() => {
          this.importFileDialog.loading = false;
          this.importFileDialog.visiable = false;
        });
    },

    // 处理下载
    invokeBrowserDownload(content, filename) {
      const a = document.createElement('a');
      const blob = new Blob([content], { type: 'text/plain' });
      a.download = filename;
      a.href = URL.createObjectURL(blob);
      a.click();
      a.remove();
      URL.revokeObjectURL(blob);
    },

    // 取消
    handleCancel() {
      this.envVarList = _.cloneDeep(this.envLocalVarList);
      this.isBatchEdit = false;
    },

    sourceFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },

    handleRenderHander(h, { $index }) {
      let columnName = 'Key';
      switch ($index) {
        case 0:
          columnName = 'Key';
          break;
        case 1:
          columnName = 'Value';
          break;
        case 2:
          columnName = this.$t('生效环境');
          break;
        default:
          break;
      }
      return h(
        'span', { class: 'custom-header-cls flex-row align-items-center' },
        [
          h('span', null, columnName),
          h('span', { class: 'header-required' }, '*'),
        ],
      );
    },

    // 单个环境编辑
    handleSingleEdit(index) {
      this.envVarList[index].isEdit = true;
    },

    // 删除单个环境变量
    async handleSingleDelete(row) {
      const deleteEnvVarData = this.envVarList.find(v => v.id === row.id);
      const varId = deleteEnvVarData.id;
      try {
        await this.$store.dispatch('envVar/deleteEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除环境变量成功'),
        });
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('删除环境变量失败')}，${e.message}`,
        });
      }
    },

    // 单个环境编辑保存
    handleSingleSave(index) {
      if (this.envVarList[index].isAdd) { // 新建
        this.singleValidate(index, 'add');
      } else { // 编辑
        this.singleValidate(index, 'update');
      }
    },

    // 新建环境变量模板
    handleAddSingleVariable() {
      const curEnvVarLength = this.envVarList.length + 1;
      if ((curEnvVarLength - this.envLocalVarList.length) <= 1) {
        this.envVarList.push({
          key: '',
          value: '',
          environment_name: 'stag',
          description: '',
          isEdit: true,
          isAdd: true,
        });
      }
    },

    // 单个环境编辑取消
    handleSingleCancel(index) {
      this.envVarList[index].isEdit = false;
      // 添加数据未保存，点击取消直接删除
      if (!this.envLocalVarList[index]) {
        this.envVarList.splice(index, 1);
      } else {
        // 编辑还原
        this.envVarList[index].key = this.envLocalVarList[index].key;
        this.envVarList[index].value = this.envLocalVarList[index].value;
        this.envVarList[index].description = this.envLocalVarList[index].description;
        this.envVarList[index].environment_name = this.envLocalVarList[index].environment_name;
      }
    },

    // 过滤环境
    handleFilterEnv(value) {
      this.activeEnvValue = value;
      // 过滤
      if (value === 'all') {
        this.envVarList = _.cloneDeep(this.envLocalVarList);
        return;
      }
      this.envVarList = this.envLocalVarList.filter(v => v.environment_name === value);
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
.env-container {
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
      border: 1px solid #3a84ff;
      color: #fff;

      &:hover {
        color: #fff;
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
  color: #979ba5;
  margin-bottom: 10px;
}

.env-table-icon {
  color: #c4c6cc;
  font-size: 14px;
  .icon {
    cursor: pointer;
  }
}

.env-from-cls {
  width: 100%;
  /deep/ .bk-form-item {
    width: 100%;
    .bk-form-content {
      width: 100%;
      .tooltips-icon {
        right: 1% !important;
      }
    }
  }
}
.env-input-cls {
  /deep/ .bk-form-input {
    width: 90%;
  }
}

.export-btn-cls {
  font-size: 12px;
}

/deep/ .header-required {
  color: #ea3636;
  padding-left: 5px;
  padding-top: 5px;
}
.env-btn-wrapper {
  margin-top: 24px;
}
.add-wrapper {
  height: 42px;
  .add-single-variable {
    display: inline-block;
    height: 42px;
    line-height: 42px;
    padding: 0 15px;
    color: #3a84ff;
    cursor: pointer;
    i {
      font-size: 16px;
      margin-right: 3px;
      transform: translateY(0px);
    }
  }
}
.variable-table-cls {
  /deep/ .bk-table-empty-block {
    display: none;
  }
}
.mr6 {
  margin-right: 6px;
}
.right {
  .paasng-upload,
  .paasng-download {
    font-size: 12px;
  }
}
.filter-action-list {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 4px;
  border-radius: 2px;
  background: #F0F1F5;

  li {
    position: relative;
    user-select: none;
    height: 100%;
    line-height: 24px;
    font-size: 12px;
    color: #63656E;
    padding: 0 15px;
    cursor: pointer;


    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      display: block;
      width: 1px;
      height: 12px;
      margin-top: -6px;
      background: #DCDEE5;
      content: "";
    }
    &:first-child::before {
      height: 0;
    }

    &.active {
      color: #3a84ff;
      background: #fff;
      border-radius: 2px;

      &::before {
        background: #fff;
      }

      & + li::before {
        height: 0;
      }
    }
  }
}
</style>
