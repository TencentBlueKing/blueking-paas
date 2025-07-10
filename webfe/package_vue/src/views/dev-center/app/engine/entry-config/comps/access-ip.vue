<template>
  <div>
    <paas-content-loader
      :is-loading="isPermissionChecking"
      placeholder="user-limit-loading"
      :offset-top="0"
      class="middle"
    >
      <section v-show="!isPermissionChecking">
        <div
          v-if="!isPermissionChecking"
          class="perm-action"
        >
          <div :class="['perm-icon', { 'active': isUseIPPermission }]">
            <span :class="['paasng-icon', { 'paasng-lock': !isUseIPPermission, 'paasng-unlock': isUseIPPermission }]" />
          </div>
          <div class="perm-title flex-row align-items-center">
            {{ $t('IP 限制 ') }}
            <div
              class="ps-switcher-wrapper"
              @click="togglePermission"
            >
              <bk-switcher
                v-model="isUseIPPermission"
              />
            </div>
            <div class="perm-status" :class="isUseIPPermission ? 'perm-status-open' : 'perm-status-close'">
              {{ isUseIPPermission ? $t('已开启') : $t('未开启') }}
            </div>
          </div>
          <p class="perm-tip">
            {{ isUseIPPermission ? $t('开启 IP 限制后，仅白名单中的 IP 才能访问应用，预发布环境、生产环境同时生效')
              : $t('开启 IP 限制后，仅白名单中的 IP 才能访问应用，预发布环境、生产环境同时生效') }}
          </p>
        </div>
        <template v-if="!isPermissionChecking && isUseIPPermission">
          <section class="table-container mt15">
            <div class="ps-table-bar">
              <bk-button
                theme="primary"
                @click="showIPModal"
              >
                <i class="paasng-icon paasng-plus mr5" /> {{ $t('添加白名单') }}
              </bk-button>
              <bk-dropdown-menu
                ref="largeDropdown"
                trigger="click"
                ext-cls="by-ip-export-wrapper"
              >
                <bk-button
                  slot="dropdown-trigger"
                  :loading="exportLoading"
                >
                  {{ $t('批量导入/导出') }}
                </bk-button>
                <ul
                  slot="dropdown-content"
                  class="bk-dropdown-list"
                >
                  <li>
                    <a
                      href="javascript:;"
                      style="margin: 0;"
                      @click="handleExport('file')"
                    > {{ $t('从文件导入') }} </a>
                  </li>
                  <li>
                    <a
                      href="javascript:;"
                      style="margin: 0;"
                      @click="handleExport('batch')"
                    > {{ $t('批量导出') }} </a>
                  </li>
                </ul>
              </bk-dropdown-menu>
              <bk-button
                style="margin-left: 6px;"
                :disabled="isBatchDisabled"
                @click="batchDelete"
              >
                {{ $t('批量删除') }}
              </bk-button>
              <bk-input
                v-model="keyword"
                style="width: 240px; float: right;"
                :placeholder="$t('输入关键字，按Enter搜索')"
                :right-icon="'paasng-icon paasng-search'"
                clearable
                @enter="searchIpList"
              />
            </div>

            <bk-table
              v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
              :data="IPPermissionList"
              size="small"
              :class="{ 'set-border': tableLoading }"
              :ext-cls="'ps-permission-table'"
              :pagination="pagination"
              @page-change="pageChange"
              @page-limit-change="limitChange"
              @select="handlerChange"
              @select-all="handlerAllChange"
            >
              <div slot="empty">
                <table-empty
                  :keyword="tableEmptyConf.keyword"
                  :abnormal="tableEmptyConf.isAbnormal"
                  @reacquire="fetchIpList(true)"
                  @clear-filter="clearFilterKey"
                />
              </div>
              <bk-table-column
                type="selection"
                width="60"
                align="left"
              />
              <bk-table-column
                label="IP/IP段"
                prop="content"
                :render-header="$renderHeader"
              />
              <bk-table-column
                :label="$t('路径')"
                prop="path"
              />
              <bk-table-column
                :label="$t('添加者')"
                :render-header="$renderHeader"
              >
                <template slot-scope="props">
                  <span>{{ props.row.owner.username || '--' }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('添加时间')"
                :render-header="renderHeader"
              >
                <template slot-scope="{ row }">
                  <span v-bk-tooltips="row.created">{{ smartTime(row.created,'fromNow') }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('更新时间')"
                :render-header="$renderHeader"
              >
                <template slot-scope="{ row }">
                  <span v-bk-tooltips="row.updated">{{ smartTime(row.updated,'fromNow') }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('添加原因')"
                :render-header="$renderHeader"
              >
                <template slot-scope="props">
                  <bk-popover>
                    <div class="reason">
                      {{ props.row.desc ? props.row.desc : '--' }}
                    </div>
                    <div
                      slot="content"
                      style="white-space: normal;"
                    >
                      {{ props.row.desc ? props.row.desc : '--' }}
                    </div>
                  </bk-popover>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('到期时间')"
                width="100"
                :render-header="$renderHeader"
              >
                <template slot-scope="{ row }">
                  <template v-if="row.is_expired">
                    <span v-bk-tooltips="row.expires_at"> {{ $t('已过期') }} </span>
                  </template>
                  <template v-else>
                    <template v-if="row.expires_at">
                      <span v-bk-tooltips="row.expires_at">{{ smartTime(row.expires_at,'fromNow') }}</span>
                    </template>
                    <template v-else>
                      {{ $t('永不') }}
                    </template>
                  </template>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('操作')"
                width="150"
              >
                <template slot-scope="props">
                  <section>
                    <bk-button
                      theme="primary"
                      text
                      @click="handleRenewal(props.row)"
                    >
                      {{ $t('续期') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      style="margin-left: 6px;"
                      @click="handleEdit(props.row)"
                    >
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      style="margin-left: 6px;"
                      @click="showRemoveModal(props.row)"
                    >
                      {{ $t('删除') }}
                    </bk-button>
                  </section>
                </template>
              </bk-table-column>
            </bk-table>
          </section>
        </template>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="IPPermissionDialog.visiable"
      width="600"
      :title="`${isUseIPPermission ? $t('是否停用 IP 限制') : $t('是否开启 IP 限制')}?`"
      :theme="'primary'"
      :mask-close="false"
      :loading="IPPermissionDialog.isLoading"
      @confirm="setIPPermission"
      @cancel="closePermission"
    >
      <div class="tc">
        {{ isUseIPPermission ? $t('停用后【预发布】和【生产】环境的 IP 限制都将立即失效，所有 IP 都可访问') : $t('开启后【预发布】和【生产】环境的 IP 限制都将立即生效，仅白名单内 IP 可访问') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="removeIPDialog.visiable"
      width="600"
      :title="`确定删除IP【${curIPParams.content}】`"
      :theme="'primary'"
      :mask-close="false"
      :loading="removeIPDialog.isLoading"
      @confirm="removeIP"
      @cancel="cancelRemoveIP"
      @after-leave="afterDeleteClose"
    >
      <div class="tc">
        {{ curIPParams.content }} {{ $t('将失去此应用的对应权限，是否确定删除？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="batchRemoveIpDialog.visiable"
      width="600"
      :title="$t('确定批量删除IP？')"
      :theme="'primary'"
      :mask-close="false"
      :loading="batchRemoveIpDialog.isLoading"
      @confirm="batchRemoveIp"
    >
      <div class="tc">
        {{ $t('批量删除的IP将失去此应用的对应权限，是否确定删除？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="renewalDialog.visiable"
      width="600"
      :title="$t('有效期续期')"
      :theme="'primary'"
      :mask-close="false"
      :header-position="'left'"
      :loading="renewalDialog.isLoading"
      @confirm="handleRenewalDialog"
      @after-leave="afterRenewalClose"
    >
      <div>
        <div class="time-button-groups bk-button-group">
          <bk-button
            v-for="(key, index) in Object.keys(timeFilters)"
            v-if="key !== 'cur'"
            :key="index"
            :class="[{ 'is-selected': key === timeFilters['cur'] }, { 'reset-width': key === 'custom' }]"
            :name="key"
            @click="timeFilterHandler(key, index)"
          >
            {{ timeFilters[key] }}
          </bk-button>
        </div>
        <div
          v-if="customTimeFlag"
          class="custom-time-select"
        >
          <input
            v-model="customTime"
            type="text"
            class="bk-form-input custom-time"
            placeholder="1"
            @input="authDetailTimeHandler"
          >
          <div class="unit">
            天
          </div>
        </div>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="addIPDialog.visiable"
      width="600"
      :title="addIPDialog.title"
      :theme="'primary'"
      :mask-close="false"
      header-position="left"
      :close-icon="!addIPDialog.isLoading"
      :loading="addIPDialog.isLoading"
      @confirm="addIP"
      @cancel="cancelAddIP"
      @after-leave="afterAddClose"
    >
      <div
        v-if="isShowAddForm"
        style="min-height: 140px;"
      >
        <bk-form
          ref="addIPForm"
          :label-width="100"
          :model="curIPParams"
          form-type="vertical"
        >
          <bk-form-item
            label="IP/IP段"
            :required="true"
            :rules="IPParamRules.content"
            :property="'content'"
          >
            <bk-input
              v-model="curIPParams.content"
              type="text"
              :maxlength="200"
              :disabled="addIPDialog.isEdit"
            />
            <p class="ps-tip mt10">
              {{ $t('多个IP请用英文分号‘;’隔开，支持掩码') }}
            </p>
          </bk-form-item>
          <bk-form-item
            :label="$t('可访问路径前缀')"
            :label-width="160"
            :rules="IPParamRules.path"
            :required="false"
            :property="'path'"
          >
            <bk-input
              v-model="curIPParams.path"
              :placeholder="$t('不填代表可访问所有路径')"
              type="text"
              :disabled="addIPDialog.isEdit"
            />
            <p class="ps-tip mt10">
              {{ $t('以反斜杆(/)开始、结束，如/api/user/表示可访问以/api/user/开头的所有路径') }}
            </p>
          </bk-form-item>
          <bk-form-item
            :label="$t('添加原因')"
            :required="true"
            :rules="IPParamRules.desc"
            :property="'desc'"
          >
            <bk-input
              v-model="curIPParams.desc"
              type="textarea"
              :placeholder="$t('请输入200个字符以内')"
              :maxlength="200"
            />
          </bk-form-item>
          <bk-form-item
            v-if="!addIPDialog.isEdit"
            :label="$t('有效时间')"
            :rules="IPParamRules.expires_at"
            :required="true"
            :property="'expires_at'"
          >
            <div class="time-button-groups bk-button-group">
              <bk-button
                v-for="(key, index) in Object.keys(timeFilters)"
                v-if="key !== 'cur'"
                :key="index"
                :class="[{ 'is-selected': key === timeFilters['cur'] }, { 'reset-width': key === 'custom' }]"
                :name="key"
                @click="timeFilterHandler(key, index)"
              >
                {{ timeFilters[key] }}
              </bk-button>
            </div>
            <div
              v-if="customTimeFlag"
              class="custom-time-select"
            >
              <input
                v-model="customTime"
                type="text"
                class="bk-form-input custom-time"
                placeholder="1"
                @input="authDetailTimeHandler"
              >
              <div class="unit">
                天
              </div>
            </div>
          </bk-form-item>
        </bk-form>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="exportFileDialog.visiable"
      :header-position="exportFileDialog.headerPosition"
      :loading="exportFileDialog.loading"
      :width="exportFileDialog.width"
      :ok-text="$t('确定导入')"
      ext-cls="paas-env-var-upload-dialog"
      @after-leave="handleExportFileLeave"
    >
      <div
        slot="header"
        class="header"
      >
        {{ $t('从文件导入IP白名单') }}
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
            style="line-height: 40px;"
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
          style="position: absolute; width: 0; height: 0;"
          @change="handleStartUpload"
        >
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :loading="exportFileDialog.loading"
          :disabled="!curFile.name"
          @click="handleExportFileConfirm"
        >
          {{ $t('确定导入') }}
        </bk-button>
        <bk-button @click="handleExportFileCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>import appBaseInfoMixin from '@/mixins/app-base-mixin';
export default {
  components: {
  },
  mixins: [appBaseInfoMixin],
  data() {
    return {
      IPPermissionList: [],
      isUseIPPermission: true,
      isPermissionChecking: true,
      keyword: '',
      curIPParams: {
        content: '',
        path: '',
        desc: '',
        expires_at: null,
      },
      inputStatus: {
        content: {
          isShow: false,
          tip: '',
        },
        path: {
          isShow: false,
          tip: '',
        },
        desc: {
          isShow: false,
          tip: '',
        },
      },
      IPPermissionDialog: {
        visiable: false,
        isLoading: false,
      },
      addIPDialog: {
        visiable: false,
        isLoading: false,
        isEdit: false,
        title: this.$t('添加IP白名单'),
      },
      removeIPDialog: {
        visiable: false,
        isLoading: false,
        id: 0,
      },
      IPParamRules: {
        content: [
          {
            required: true,
            message: this.$t('请输入IP/IP段'),
            trigger: 'blur',
          },
          {
            validator: value => /([0,1]?\d{1,2}|2([0-4][0-9]|5[0-5]))(\.([0,1]?\d{1,2}|2([0-4][0-9]|5[0-5]))){3}/.test(value),
            trigger: 'blur',
            message: this.$t('IP/IP段格式不正确'),
          },
        ],
        path: [
          // {
          //     required: true,
          //     message: '请输入限制路径前缀',
          //     trigger: 'blur'
          // },
          {
            validator: (value) => {
              if (value === '') {
                return true;
              }
              if (this.addIPDialog.isEdit && value === '*') {
                return true;
              }
              // return /(^\/(.+\/)+)$/.test(value);
              // 避免 ReDOS 风险
              return value.startsWith('/') && value.endsWith('/') && value.length > 2;
            },
            message: this.$t('可访问路径前缀格式错误，以反斜杠(/)开始、结束，如：/api/user/'),
            trigger: 'blur',
          },
        ],
        desc: [
          {
            required: true,
            message: this.$t('请输入添加原因'),
            trigger: 'blur',
          },
        ],
      },

      tableLoading: false,

      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },

      is_up: true,

      isFilter: false,

      currentBackup: 1,

      isShowAddForm: false,

      currentSelectList: [],

      batchRemoveIpDialog: {
        visiable: false,
        isLoading: false,
      },

      customTime: 1,
      timeFilters: {
        month: this.$t('1个月'),
        month3: this.$t('3个月'),
        month6: this.$t('6个月'),
        month12: this.$t('12个月'),
        forever: this.$t('永久'),
        custom: this.$t('自定义'),
        cur: 'forever',
      },

      renewalDialog: {
        visiable: false,
        isLoading: false,
        id: 0,
      },

      renewalParams: {
        expires: '',
        expires_at: null,
      },

      exportLoading: false,
      exportFileDialog: {
        visiable: false,
        width: 540,
        headerPosition: 'center',
        loading: false,
      },
      curFile: {},
      isFileTypeError: false,
      tableEmptyConf: {
        keyword: '',
        isAbnormal: false,
      },
    };
  },
  computed: {
    isBatchDisabled() {
      return this.currentSelectList.length < 1 || this.IPPermissionList.length < 1;
    },
    customTimeFlag() {
      return this.timeFilters.cur === 'custom';
    },
    curModule() {
      return this.curAppModuleList.find(item => item.is_default);
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
    'pagination.current'(value) {
      this.currentBackup = value;
    },
    keyword(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        if (this.isFilter) {
          this.pagination.current = 1;
          this.pagination.limit = 10;
          this.fetchIpList(true);
          this.isFilter = false;
        }
      }
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    handleExport(type) {
      this.$refs.largeDropdown.hide();
      switch (type) {
        case 'file':
          this.exportFileDialog.visiable = true;
          break;
        case 'batch':
          this.handleBatchExport();
          break;
        default:
          break;
      }
    },

    downloadYaml(content, type = 'download') {
      const fileName = type === 'download' ? 'whitelist_import_template' : `${this.appCode}_ip_whitelist`;
      const elment = document.createElement('a');
      const blob = new Blob([content], {
        type: 'text/plain',
      });
      elment.download = `${fileName}.yaml`;
      elment.href = URL.createObjectURL(blob);
      elment.click();
      URL.revokeObjectURL(blob);
    },

    handleExportFileConfirm() {
      this.exportFileDialog.loading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/ip/strategy/import/`;
      const params = new FormData();
      params.append('file', this.curFile);
      this.$http.post(url, params).then((response) => {
        const createNum = response.create_num;
        const overwritedNum = response.overwrited_num;
        const ignoreNum = response.ignore_num;
        this.isEdited = createNum > 0 || overwritedNum > 0;
        const message = (
          () => {
            const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(Boolean(ignoreNum))}`;
            let messageText = '';
            switch (numStr) {
              case '111':
                messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个IP白名单，更新')} ${overwritedNum} ${this.$t('个IP白名单，忽略')} ${ignoreNum} ${this.$t('个白名单')}`;
                break;
              case '110':
                messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个IP白名单，更新')} ${overwritedNum} ${this.$t('个IP白名单')}`;
                break;
              case '100':
                messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个IP白名单')}`;
                break;
              case '101':
                messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个IP白名单，忽略')} ${ignoreNum} ${this.$t('个IP白名单')}`;
                break;
              case '011':
                messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个IP白名单，忽略')} ${ignoreNum} ${this.$t('个IP白名单')}`;
                break;
              case '010':
                messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个IP白名单')}`;
                break;
              case '001':
                messageText = this.$t('所有IP白名单都已在当前模块中，已全部忽略');
                break;
              default:
                messageText = `${this.$t('导入成功')}`;
            }
            return messageText;
          }
        )();
        this.$paasMessage({
          theme: 'success',
          message,
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.fetchIpList(true);
      }, (errRes) => {
        const errorMsg = errRes.detail;
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('从文件导入IP白名单失败')}，${errorMsg}`,
        });
      })
        .finally(() => {
          this.exportFileDialog.loading = false;
          this.exportFileDialog.visiable = false;
        });
    },

    handleExportFileLeave() {
      this.curFile = {};
      this.isFileTypeError = false;
    },

    handleExportFileCancel() {
      this.exportFileDialog.visiable = false;
    },

    handleBatchExport() {
      const orderBy = this.is_up ? '-created' : 'created';
      this.exportLoading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/ip/strategy/export/?order_by=${orderBy}`;
      this.$http.get(url).then((response) => {
        this.downloadYaml(response.body, 'export');
      }, (errRes) => {
        const errorMsg = errRes.detail;
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
        });
      })
        .finally(() => {
          this.exportLoading = false;
        });
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

    handleDownloadTemplate() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/ip/strategy/export/template/`;
      this.$http.get(url).then((response) => {
        this.downloadYaml(response.body);
      }, (errRes) => {
        const errorMsg = errRes.message;
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('获取yaml模板失败')}，${errorMsg}`,
        });
      });
    },

    async handleRenewalDialog() {
      this.renewalDialog.isLoading = true;
      try {
        await this.$store.dispatch('ip/ipPermissinRenewal', {
          appCode: this.appCode,
          id: this.renewalDialog.id,
          params: this.renewalParams,
        });
        this.currentSelectList = [];
        this.fetchIpList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('续期成功'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('续期失败：')} ${e.detail}`,
        });
      } finally {
        this.renewalDialog.isLoading = false;
        this.renewalDialog.visiable = false;
      }
    },

    afterRenewalClose() {
      this.renewalDialog.id = 0;
      this.curIPParams.content = '';
      this.curIPParams.desc = '';
      this.curIPParams.path = '';
      this.curIPParams.expires_at = null;
      this.renewalParams.expires_at = null;
      this.renewalParams.expires = '';
      this.timeFilters = Object.assign({}, {
        month: this.$t('1个月'),
        month3: this.$t('3个月'),
        month6: this.$t('6个月'),
        month12: this.$t('12个月'),
        forever: this.$t('永久'),
        custom: this.$t('自定义'),
        cur: 'forever',
      });
      this.customTime = 1;
    },

    timeFilterHandler(key) {
      const currentTimestamp = new Date().getTime();
      if (key === 'custom') {
        this.$delete(this.timeFilters, 'custom');
      } else {
        this.$set(this.timeFilters, 'custom', this.$t('自定义'));
      }
      this.timeFilters.cur = key;
      if (key === 'forever') {
        this.curIPParams.expires_at = null;

        this.renewalParams.expires_at = null;
        this.renewalParams.expires = '';
      } else {
        const date = this.timestampToTime(currentTimestamp + this.timeToSecond(key) * 1000);
        this.curIPParams.expires_at = date;

        this.renewalParams.expires_at = '';
        this.renewalParams.expires = `${this.timeToHour(key)}:00:00`;
      }
    },

    timestampToTime(timestamp) {
      let time = '';
      if (timestamp) {
        time = new Date(timestamp);
      } else {
        time = new Date();
      }
      const Y = `${time.getFullYear()}-`;
      const M = `${time.getMonth() + 1 < 10 ? `0${time.getMonth() + 1}` : time.getMonth() + 1}-`;
      const D = (time.getDate() < 10 ? `0${time.getDate()}` : time.getDate());
      const h = `${time.getHours() < 10 ? `0${time.getHours()}` : time.getHours()}:`;
      const m = `${time.getMinutes() < 10 ? `0${time.getMinutes()}` : time.getMinutes()}:`;
      const s = (time.getSeconds() < 10 ? `0${time.getSeconds()}` : time.getSeconds());
      return `${Y + M + D} ${h}${m}${s}`;
    },

    authDetailTimeHandler(e) {
      if (e.target.value === '') {
        const currentTimestampNow = new Date().getTime();
        const nowDate = this.timestampToTime(currentTimestampNow + 24 * 3600 * 1000);
        this.curIPParams.expires_at = nowDate;

        this.renewalParams.expires_at = '';
        this.renewalParams.expires = '24:00:00';
        return;
      }
      if (!/^[0-9]*$/.test(e.target.value)) {
        this.customTime = 1;
        return;
      }
      if (e.target.value.length === 1) {
        this.customTime = e.target.value.replace(/[^1-9]/g, '');
      } else {
        this.customTime = e.target.value.replace(/\D/g, '');
      }
      if (e.target.value > 365 && e.target.value.length === 3) {
        this.customTime = 365;
      } else {
        if (e.target.value.length > 3) {
          this.customTime = parseInt(e.target.value.slice(0, 3), 10);
        }
      }
      const currentTimestamp = new Date().getTime();
      const date = this.timestampToTime(currentTimestamp + Number(this.customTime) * 24 * 3600 * 1000);
      this.curIPParams.expires_at = date;

      this.renewalParams.expires_at = '';
      this.renewalParams.expires = `${Number(this.customTime) * 24}:00:00`;
    },

    timeToSecond(cur) {
      let s = 0;
      switch (cur) {
        case 'month':
          s = 30 * 24 * 3600;
          break;
        case 'month3':
          s = 3 * 30 * 24 * 3600;
          break;
        case 'month6':
          s = 6 * 30 * 24 * 3600;
          break;
        case 'month12':
          s = (12 * 30 + 5) * 24 * 3600;
          break;
        case 'forever':
          s = 0;
          break;
        case 'custom':
          s = 24 * 3600;
          break;
        default:
          s = 0;
      }
      return s;
    },

    timeToHour(cur) {
      let h = 0;
      switch (cur) {
        case 'month':
          h = 30 * 24;
          break;
        case 'month3':
          h = 3 * 30 * 24;
          break;
        case 'month6':
          h = 6 * 30 * 24;
          break;
        case 'month12':
          h = (12 * 30 + 5) * 24;
          break;
        case 'forever':
          h = 0;
          break;
        case 'custom':
          h = 24;
          break;
        default:
          h = 0;
      }
      return h;
    },

    sortTab() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
      this.pagination.current = 1;
      this.pagination.limit = 10;
      this.fetchIpList(true);
    },

    batchDelete() {
      if (this.currentSelectList.length === 1) {
        const { id } = this.currentSelectList[0];
        [this.curIPParams] = this.currentSelectList;
        this.removeIPDialog.id = id;
        this.removeIPDialog.visiable = true;
        return;
      }
      this.batchRemoveIpDialog.visiable = true;
    },

    handleRenewal(row) {
      this.renewalDialog.id = row.id;
      this.renewalDialog.visiable = true;
    },

    async batchRemoveIp() {
      this.batchRemoveIpDialog.isLoading = true;
      try {
        await this.$store.dispatch('ip/deleteIp', {
          appCode: this.appCode,
          ids: this.currentSelectList.map(item => item.id),
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchIpList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('批量删除成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('批量删除失败：')} ${e.detail}`,
        });
      } finally {
        this.batchRemoveIpDialog.isLoading = false;
        this.batchRemoveIpDialog.visiable = false;
      }
    },

    handlerAllChange(selection) {
      this.currentSelectList = [...selection];
    },

    handlerChange(selection) {
      this.currentSelectList = [...selection];
    },

    renderHeader(h) {
      return h(
        'div',
        {
          on: {
            click: this.sortTab,
          },
          style: {
            cursor: this.pagination.count ? 'pointer' : 'not-allowed',
          },
        },
        [
          h('span', {
            domProps: {
              innerHTML: this.$t('添加时间'),
            },
          }),
          h('img', {
            style: {
              position: 'relative',
              top: '1px',
              left: '1px',
              transform: this.is_up ? 'rotate(0)' : 'rotate(180deg)',
            },
            attrs: {
              src: '/static/images/sort-icon.png',
            },
          }),
        ],
      );
    },

    searchIpList() {
      if (this.keyword === '') {
        return;
      }
      this.isFilter = true;
      this.pagination.limit = 10;
      this.pagination.current = 1;
      this.fetchIpList(true);
    },

    /**
               * 分页页码 chang 回调
               *
               * @param {Number} page 页码
               */
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
      this.fetchIpList(true);
    },

    /**
     * 分页limit chang 回调
     *
     * @param {Number} currentLimit 新limit
     * @param {Number} prevLimit 旧limit
     */
    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
      this.fetchIpList(true);
    },

    clearKeyword() {
      this.keyword = '';
    },

    togglePermission() {
      this.IPPermissionDialog.visiable = true;
    },

    handleEdit(row) {
      const { content, path, desc, id, expires_at } = row;
      this.curIPParams = {
        content,
        path,
        desc,
        expires_at,
      };
      this.renewalDialog.id = id;
      this.addIPDialog.title = this.$t('编辑IP白名单');
      this.addIPDialog.isEdit = true;
      this.addIPDialog.visiable = true;
      this.isShowAddForm = true;
    },

    showIPModal() {
      this.addIPDialog.visiable = true;
      this.isShowAddForm = true;
    },

    showRemoveModal(user) {
      this.curIPParams = user;
      this.removeIPDialog.visiable = true;
      this.removeIPDialog.id = user.id;
    },

    async setIPPermission() {
      this.IPPermissionDialog.isLoading = true;
      try {
        await this.$store.dispatch('ip/setIpPermissin', {
          appCode: this.appCode,
          is_enabled: !this.isUseIPPermission,
        });
        this.isUseIPPermission = !this.isUseIPPermission;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail,
        });
      } finally {
        this.IPPermissionDialog.isLoading = false;
        this.closePermission();
      }
    },

    closePermission() {
      this.IPPermissionDialog.visiable = false;
    },

    async checkIPPermissin() {
      this.isPermissionChecking = true;
      try {
        const res = await this.$store.dispatch('ip/checkIpPermissin', {
          appCode: this.appCode,
        });
        this.isUseIPPermission = res.is_enabled;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail,
        });
      } finally {
        this.isPermissionChecking = false;
      }
    },

    async fetchIpList(isTableLoading = false) {
      this.tableLoading = isTableLoading;
      try {
        const params = {
          appCode: this.appCode,
          limit: this.pagination.limit,
          offset: (this.pagination.current - 1) * this.pagination.limit,
          order_by: this.is_up ? '-created' : 'created',
          search_term: this.keyword,
        };

        const res = await this.$store.dispatch('ip/getIpList', params);
        this.pagination.count = res.count;
        this.IPPermissionList.splice(0, this.IPPermissionList.length, ...(res.results || []));
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取IP名单失败：')} ${e.detail}`,
        });
      } finally {
        if (isTableLoading) {
          this.tableLoading = false;
        }
      }
    },

    clearInputStatus(type) {
      if (type) {
        this.inputStatus[type] = {
          isShow: false,
          tip: '',
        };
      } else {
        this.inputStatus = {
          content: {
            isShow: false,
            tip: '',
          },
          path: {
            isShow: false,
            tip: '',
          },
          desc: {
            isShow: false,
            tip: '',
          },
        };
      }
    },

    checkUserParams(params) {
      const contentReg = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/([1-9]|[1-2][0-9]|3[0-2]))?$/;
      const text = this.addIPDialog.isEdit ? this.$t('编辑') : this.$t('添加');
      if (!params.content) {
        this.$paasMessage({
          theme: 'error',
          message: `${text}${this.$t('IP白名单失败：')} ${this.$t('请输入IP/IP段！')}`,
        });
        this.inputStatus.content = {
          isShow: true,
          tip: this.$t('请输入IP/IP段！'),
        };
        return false;
      }

      const checkList = params.content.trim().split(';')
        .filter(item => item !== '');
      for (const item of checkList) {
        if (!contentReg.test(item)) {
          this.$paasMessage({
            theme: 'error',
            message: `${text}${this.$t('IP白名单失败：')} ${this.$t('请输入合法的IP/IP段！')}}`,
          });
          this.inputStatus.content = {
            isShow: true,
            tip: this.$t('请输入合法的IP/IP段！'),
          };
          return false;
        }
      }

      // if (!params.path) {
      //     this.$paasMessage({
      //         theme: 'error',
      //         message: '新增IP失败： 请输入限制路径！'
      //     })
      //     this.inputStatus.path = {
      //         isShow: true,
      //         tip: '请输入限制路径！'
      //     }
      //     return false
      // }

      if (!params.desc) {
        this.$paasMessage({
          theme: 'error',
          message: `${text}${this.$t('IP失败：')} ${this.$t('请输入添加原因！')}`,
        });
        this.inputStatus.desc = {
          isShow: true,
          tip: this.$t('请输入添加原因！'),
        };
        return false;
      }

      this.clearInputStatus();
      return true;
    },

    addIP() {
      const params = this.curIPParams;

      this.addIPDialog.isLoading = true;
      setTimeout(() => {
        this.$refs.addIPForm.validate().then(
          () => {
            if (this.checkUserParams(params)) {
              this.submitIPParams(params);
            } else {
              this.addIPDialog.isLoading = false;
            }
          },
          () => {
            this.addIPDialog.isLoading = false;
          },
        );
      }, 200);
    },

    async submitIPParams(params) {
      if (this.addIPDialog.isEdit) {
        this.handleEditIp(params);
      } else {
        this.handleAddIp(params);
      }
    },

    async handleAddIp(payload = {}) {
      this.addIPDialog.isLoading = true;
      const params = JSON.parse(JSON.stringify(payload));
      params.content = params.content.trim().split(';')
        .filter(item => item !== '')
        .join(';');
      try {
        await this.$store.dispatch('ip/addIp', {
          appCode: this.appCode,
          params,
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.fetchIpList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('添加失败：')} ${e.detail}`,
        });
      } finally {
        this.addIPDialog.isLoading = false;
        this.cancelAddIP();
      }
    },

    async handleEditIp(params = {}) {
      this.addIPDialog.isLoading = true;
      try {
        await this.$store.dispatch('ip/ipPermissinRenewal', {
          appCode: this.appCode,
          id: this.renewalDialog.id,
          params,
        });
        this.fetchIpList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('编辑失败：')} ${e.detail}`,
        });
      } finally {
        this.addIPDialog.isLoading = false;
        this.cancelAddIP();
      }
    },

    async removeIP() {
      this.removeIPDialog.isLoading = true;
      try {
        await this.$store.dispatch('ip/deleteIp', {
          appCode: this.appCode,
          ids: [this.removeIPDialog.id],
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchIpList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('删除失败：')} ${e.detail}`,
        });
      } finally {
        this.removeIPDialog.isLoading = false;
        this.cancelRemoveIP();
      }
    },

    afterDeleteClose() {
      this.curIPParams = JSON.parse(JSON.stringify({
        content: '',
        path: '',
        desc: '',
        expires_at: null,
      }));
      this.removeIPDialog.id = 0;
    },

    cancelRemoveIP() {
      this.removeIPDialog.visiable = false;
    },

    afterAddClose() {
      this.curIPParams = {
        content: '',
        path: '',
        desc: '',
        expires_at: null,
      };
      this.renewalDialog.id = 0;
      this.addIPDialog.title = '添加IP白名单';
      this.addIPDialog.isEdit = false;
      this.clearInputStatus(0);
      this.isShowAddForm = false;
      this.timeFilters = Object.assign({}, {
        month: this.$t('1个月'),
        month3: this.$t('3个月'),
        month6: this.$t('6个月'),
        month12: this.$t('12个月'),
        forever: this.$t('永久'),
        custom: this.$t('自定义'),
        cur: 'forever',
      });
      this.customTime = 1;
    },

    cancelAddIP() {
      this.addIPDialog.visiable = false;
    },

    init() {
      this.$refs.moduleRef && this.$refs.moduleRef.setCurModule(this.curModule);
      this.checkIPPermissin();
      this.fetchIpList(true);
    },

    clearFilterKey() {
      this.keyword = '';
    },

    updateTableEmptyConfig() {
      this.tableEmptyConf.keyword = this.keyword;
    },
  },
};
</script>

  <style lang="scss" scoped>
      .bk-table {
          &.set-border {
              border-right: 1px solid #dfe0e5;
              border-bottom: 1px solid #dfe0e5;
          }
      }

      .perm-action {
          position: relative;
          overflow: hidden;
          background: #fff;
          padding: 20px 24px;

          .perm-icon {
              float: left;
              width: 42px;
              height: 42px;
              margin-right: 12px;
              background: rgba(195, 205, 215, 1);
              border-radius: 2px;
              color: #fff;
              line-height: 40px;
              font-size: 22px;
              text-align: center;

              &.active {
                  background-color: rgba(48, 216, 120, 1);
              }
          }

          .perm-title {
              font-size: 14px;
              color: #313238;
              margin-bottom: 5px;
              line-height: 1;
              font-weight: 700;
              .perm-status{
                border-radius: 2px;
                width: 52px;
                height: 22px;
                text-align: center;
                line-height: 22px;
                margin-left: 15px;
                font-size: 12px;
              }
              .perm-status-open{
                color: #14A568;
                background: #E4FAF0;
              }
              .perm-status-close{
                color: #fff;
                background-color: #dcdee5;
              }
          }

          .perm-tip {
              line-height: 1;
              font-size: 12px;
              color: #979BA5;
          }
      }

      .table-container{
        background: #fff;
        padding: 0px 24px 20px;
        .ps-table-bar {
            position: relative;
            padding: 16px 0;
            border-top: 1px solid #e6e9ea;
            .path-exempt {
                position: absolute;
                top: 20px;
                left: 336px;
                &.en-path {
                    left: 382px;
                }
            }

        }
      }

      .container {
          width: 100%;
          padding: 20px 0;
          color: #666;
      }

      .ps-table-bar {
          padding: 16px 0;
          border-top: 1px solid #e6e9ea;

      }

      .ps-search-input {
          float: right;
          margin-top: -2px;

          .paasng-close {
              font-size: 12px;
              cursor: pointer;
          }
      }

      .middle {
          border-bottom: none;
      }

      .reason {
          max-width: 130px;
          white-space: nowrap;
          word-wrap: break-word;
          word-break: break-all;
          overflow: hidden;
          text-overflow: ellipsis;
      }

      .time-button-groups {
          vertical-align: bottom;
          font-size: 0;
          button {
              width: 90px;
              &:hover {
                  color: #3a84ff;
              }
              &.reset-width {
                  width: 106px;
              }
          }
      }
      .custom-time-select {
          display: inline-block;
          margin-left: -5px;
          width: 68px;
          height: 32px;
          font-size: 0;
          vertical-align: bottom;
          input.custom-time {
              width: 67px;
              height: 32px;
              border-radius: 0;
              border: 1px solid #c3cdd7;
          }
          .unit {
              position: relative;
              top: -32px;
              right: -38px;
              width: 40px;
              height: 32px;
              line-height: 32px;
              text-align: center;
              border: 1px solid #c3cdd7;
              float: right;
              font-size: 12px;
          }
          input.custom-time:focus {
              border-color: #c3cdd7 !important;
              outline: none !important;
              box-shadow: none !important;
          }
      }

      .by-ip-export-wrapper {
          margin-left: 6px;
          vertical-align: bottom;
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
  </style>
