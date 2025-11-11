<template>
  <div>
    <paas-content-loader
      :is-loading="isPermissionChecking"
      placeholder="user-limit-loading"
      :offset-top="0"
      class="access-user"
    >
      <section>
        <div
          v-if="!isPermissionChecking"
          class="perm-action"
        >
          <div :class="['perm-icon', { active: isUseUserPermission }]">
            <span
              :class="['paasng-icon', { 'paasng-lock': !isUseUserPermission, 'paasng-unlock': isUseUserPermission }]"
            ></span>
          </div>
          <div class="perm-title flex-row align-items-center">
            {{ $t('用户限制') }}
            <div
              class="ps-switcher-wrapper"
              @click="togglePermission"
            >
              <bk-switcher v-model="isUseUserPermission" />
            </div>
            <div
              class="perm-status"
              :class="isUseUserPermission ? 'perm-status-open' : 'perm-status-close'"
            >
              {{ isUseUserPermission ? $t('已开启') : $t('未开启') }}
            </div>
          </div>
          <p class="perm-tip">
            {{ $t('启用用户限制后，仅白名单用户可访问应用主模块，预发布和生产环境同时生效。') }}
            <a
              class="a-link"
              :href="GLOBAL.DOC.ACCESS_CONTROL"
              target="_blank"
            >
              {{ $t('功能说明') }}
            </a>
          </p>
        </div>
        <template v-if="!isPermissionChecking && isUseUserPermission">
          <div class="bk-button-group mt15">
            <bk-button
              v-for="(panel, index) in userPanels"
              :key="index"
              @click="active = panel.name"
              :class="active === panel.name ? 'is-selected' : ''"
            >
              {{ panel.label }}
            </bk-button>
          </div>
          <section
            class="table-container mt15"
            v-if="active === 'whiteList'"
          >
            <div class="ps-table-bar">
              <bk-button
                theme="primary"
                @click="showUserModal"
              >
                <i class="paasng-icon paasng-plus mr5" />
                {{ $t('添加白名单') }}
              </bk-button>
              <bk-dropdown-menu
                ref="largeDropdown"
                trigger="click"
                ext-cls="by-user-export-wrapper"
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
                      style="margin: 0"
                      @click="handleExport('file')"
                    >
                      {{ $t('从文件导入') }}
                    </a>
                  </li>
                  <li>
                    <a
                      href="javascript:;"
                      style="margin: 0"
                      @click="handleExport('batch')"
                    >
                      {{ $t('批量导出') }}
                    </a>
                  </li>
                </ul>
              </bk-dropdown-menu>
              <bk-button
                style="margin-left: 6px"
                :disabled="isBatchDisabled"
                @click="batchDelete"
              >
                {{ $t('批量删除') }}
              </bk-button>
              <bk-input
                v-model="keyword"
                style="width: 240px; float: right"
                :placeholder="$t('输入关键字，按Enter搜索')"
                :right-icon="'paasng-icon paasng-search'"
                clearable
                @enter="searchUserPermissionList"
              />
            </div>

            <bk-table
              v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
              :data="userPermissionList"
              size="small"
              :class="{ 'set-border': tableLoading }"
              :pagination="pagination"
              :ext-cls="'ps-permission-table'"
              @page-change="pageChange"
              @page-limit-change="limitChange"
              @select="handlerChange"
              @select-all="handlerAllChange"
            >
              <div slot="empty">
                <table-empty
                  :keyword="tableEmptyConf.keyword"
                  :abnormal="tableEmptyConf.isAbnormal"
                  @reacquire="fetchUserPermissionList(true)"
                  @clear-filter="clearFilterKey"
                />
              </div>
              <bk-table-column
                type="selection"
                width="60"
                align="left"
              />
              <bk-table-column
                :label="userTypeMap[userType]"
                prop="content"
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
                :show-overflow-tooltip="false"
              >
                <template slot-scope="{ row }">
                  <span v-bk-tooltips="row.created">{{ smartTime(row.created, 'fromNow') }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('更新时间')"
                :render-header="$renderHeader"
                :show-overflow-tooltip="false"
              >
                <template slot-scope="{ row }">
                  <span v-bk-tooltips="row.updated">{{ smartTime(row.updated, 'fromNow') }}</span>
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('添加原因')"
                :render-header="$renderHeader"
              >
                <template slot-scope="props">
                  {{ props.row.desc ? props.row.desc : '--' }}
                </template>
              </bk-table-column>
              <bk-table-column
                :label="$t('到期时间')"
                width="100"
                :render-header="$renderHeader"
              >
                <template slot-scope="{ row }">
                  <template v-if="row.is_expired">
                    <span v-bk-tooltips="row.expires_at">{{ $t('已过期') }}</span>
                  </template>
                  <template v-else>
                    <template v-if="row.expires_at">
                      <span v-bk-tooltips="row.expires_at">{{ smartTime(row.expires_at, 'fromNow') }}</span>
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
                      style="margin-left: 6px"
                      @click="handleEdit(props.row)"
                    >
                      {{ $t('编辑') }}
                    </bk-button>
                    <bk-button
                      theme="primary"
                      text
                      style="margin-left: 6px"
                      @click="showRemoveModal(props.row)"
                    >
                      {{ $t('删除') }}
                    </bk-button>
                  </section>
                </template>
              </bk-table-column>
            </bk-table>
          </section>
          <section v-if="active === 'exemptPath'">
            <access-path></access-path>
          </section>
        </template>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="userPermissionDialog.visiable"
      width="600"
      :title="`${isUseUserPermission ? $t('是否停用用户限制') : $t('是否开启用户限制')}?`"
      :theme="'primary'"
      :mask-close="false"
      :header-position="'left'"
      :loading="userPermissionDialog.isLoading"
      @confirm="setUserPermission"
      @cancel="closePermission"
    >
      <div class="tl">
        {{
          isUseUserPermission
            ? $t('功能停用后，主模块的预发布和生产环境的用户限制将立即取消，所有用户均可访问。')
            : $t('功能开启后，预发布和生产环境的用户限制将立即生效，仅限白名单用户访问，且该限制仅适用于主模块。')
        }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="removeUserDialog.visiable"
      width="600"
      :header-position="'left'"
      :title="`${$t('确定删除名单')}【${curUserParams.content}】`"
      :theme="'primary'"
      :mask-close="false"
      :loading="removeUserDialog.isLoading"
      @confirm="removeUser"
      @after-leave="afterCloseRemove"
    >
      <div class="tl">{{ curUserParams.content }} {{ $t('将失去此应用的对应权限，是否确定删除？') }}</div>
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
          />
          <div class="unit">
            {{ $t('天') }}
          </div>
        </div>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="batchRemoveUserDialog.visiable"
      width="600"
      :title="$t('确定批量删除名单？')"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="batchRemoveUserDialog.isLoading"
      @confirm="batchRemoveUser"
    >
      <div class="tl">
        {{ $t('批量删除的名单将失去此应用的对应权限，是否确定删除？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="addUserDialog.visiable"
      width="600"
      :title="addUserDialog.title"
      header-position="left"
      :theme="'primary'"
      :mask-close="false"
      :close-icon="!addUserDialog.isLoading"
      :loading="addUserDialog.isLoading"
      @confirm="addUser"
      @cancel="cancelAddUser"
      @after-leave="afterAddClose"
    >
      <section
        v-if="addUserDialog.showForm"
        style="min-height: 140px"
      >
        <bk-form
          ref="addUserForm"
          :label-width="100"
          :model="curUserParams"
          form-type="vertical"
        >
          <bk-form-item
            :label="`${userTypeMap[userType]}`"
            :rules="userParamRules.content"
            :required="true"
            :property="'content'"
          >
            <template v-if="userType === 'rtx'">
              <user
                ref="member_selector"
                v-model="rtxList"
                :disabled="addUserDialog.isEdit"
                @change="updateCurUserContent"
              />
            </template>
            <template v-else>
              <bk-input
                v-model="curUserParams.content"
                :disabled="addUserDialog.isEdit"
              />
              <p class="ps-tip mt10">
                {{ $t('多个QQ请用英文分号‘;’隔开') }}
              </p>
            </template>
          </bk-form-item>
          <bk-form-item
            :label="$t('添加原因')"
            :rules="userParamRules.desc"
            :required="true"
            :property="'desc'"
          >
            <bk-input
              v-model="curUserParams.desc"
              type="textarea"
              :placeholder="$t('请输入200个字符以内')"
              :maxlength="200"
            />
          </bk-form-item>
          <bk-form-item
            v-if="!addUserDialog.isEdit"
            :label="$t('有效时间')"
            :rules="userParamRules.expires_at"
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
              />
              <div class="unit">
                {{ $t('天') }}
              </div>
            </div>
          </bk-form-item>
        </bk-form>
      </section>
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

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import user from '@/components/user';
import accessPath from './access-path.vue';

export default {
  components: {
    user,
    accessPath,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      userPermissionList: [],
      isUseUserPermission: true,
      isPermissionChecking: true,
      isAjaxSending: false,
      keyword: '',
      userTypeMap: {
        rtx: this.$t('姓名'),
        qq: 'QQ',
      },
      rtxList: [],
      userType: '',
      curUserParams: {
        content: '',
        desc: '',
        expires_at: null,
      },
      userParamRules: {
        content: [
          {
            required: true,
            message: this.$t('请输入'),
            trigger: 'blur',
          },
        ],
        desc: [
          {
            required: true,
            message: this.$t('请输入'),
            trigger: 'blur',
          },
        ],
      },
      userPermissionDialog: {
        visiable: false,
        isLoading: false,
      },
      addUserDialog: {
        visiable: false,
        isLoading: false,
        showForm: false,
        isEdit: false,
        title: this.$t('添加用户白名单'),
      },
      removeUserDialog: {
        visiable: false,
        isLoading: false,
        id: 0,
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

      currentSelectList: [],

      batchRemoveUserDialog: {
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
      userPanels: [{ name: 'whiteList', label: this.$t('白名单') }],
      active: 'whiteList',
    };
  },
  computed: {
    isBatchDisabled() {
      return this.currentSelectList.length < 1 || this.userPermissionList.length < 1;
    },
    customTimeFlag() {
      return this.timeFilters.cur === 'custom';
    },
    // 是否为外部版应用
    isExternal() {
      return this.curAppInfo.application.region === 'tencent';
    },
    curModule() {
      return this.curAppModuleList.find((item) => item.is_default);
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    $route() {
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
          this.fetchUserPermissionList(true);
          this.isFilter = false;
        }
      }
    },
    'curAppInfo.feature.ACCESS_CONTROL_EXEMPT_MODE': {
      // 是否可以开启豁免路径
      handler(value) {
        const hasExemptPathTag = this.userPanels.find((e) => e.name === 'exemptPath');
        if (value) {
          if (!hasExemptPathTag) {
            this.userPanels.push({ name: 'exemptPath', label: this.$t('豁免路径') });
          }
        } else {
          this.userPanels = [{ name: 'whiteList', label: this.$t('白名单') }];
        }
      },
      immediate: true,
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    timeFilterHandler(key) {
      const currentTimestamp = new Date().getTime();
      if (key === 'custom') {
        this.$delete(this.timeFilters, 'custom');
      } else {
        this.$set(this.timeFilters, 'custom', this.$t('自定义'));
      }
      this.timeFilters.cur = key;
      if (key === 'forever') {
        this.curUserParams.expires_at = null;

        this.renewalParams.expires_at = null;
        this.renewalParams.expires = '';
      } else {
        const date = this.timestampToTime(currentTimestamp + this.timeToSecond(key) * 1000);
        this.curUserParams.expires_at = date;

        this.renewalParams.expires_at = '';
        this.renewalParams.expires = `${this.timeToHour(key)}:00:00`;
      }
    },

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
      const fileName = type === 'download' ? 'whitelist_import_template' : `${this.appCode}_user_whitelist`;
      const elment = document.createElement('a');
      const blob = new Blob([content], {
        type: 'text/plain',
      });
      elment.download = `bk_paas3_${fileName}.yaml`;
      elment.href = URL.createObjectURL(blob);
      elment.click();
      URL.revokeObjectURL(blob);
    },

    handleExportFileConfirm() {
      this.exportFileDialog.loading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/user/strategy/import/`;
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
              const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(
                Boolean(ignoreNum)
              )}`;
              let messageText = '';
              switch (numStr) {
                case '111':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个IP白名单，更新'
                  )} ${overwritedNum} ${this.$t('个IP白名单，忽略')} ${ignoreNum} ${this.$t('个白名单')}`;
                  break;
                case '110':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个IP白名单，更新'
                  )} ${overwritedNum} ${this.$t('个IP白名单')}`;
                  break;
                case '100':
                  messageText = `${this.$t('导入成功')}，${this.$t('新增')} ${createNum} ${this.$t('个IP白名单')}`;
                  break;
                case '101':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个IP白名单，忽略'
                  )} ${ignoreNum} ${this.$t('个IP白名单')}`;
                  break;
                case '011':
                  messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t(
                    '个IP白名单，忽略'
                  )} ${ignoreNum} ${this.$t('个IP白名单')}`;
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
            })();
            this.$paasMessage({
              theme: 'success',
              message,
            });
            this.pagination.current = 1;
            this.pagination.limit = 10;
            this.fetchUserPermissionList(true);
          },
          (errRes) => {
            if (errRes.status === 400) {
              const errorMsg = errRes.detail;
              this.$paasMessage({
                theme: 'error',
                message: `${this.$t('从文件导入IP白名单失败')}，${errorMsg}`,
              });
            }
          }
        )
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
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/user/strategy/export/?order_by=${orderBy}`;
      this.$http
        .get(url)
        .then(
          (response) => {
            this.downloadYaml(response, 'export');
          },
          (errRes) => {
            if (errRes.status === 400) {
              const errorMsg = errRes.detail;
              this.$paasMessage({
                theme: 'error',
                message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
              });
            }
          }
        )
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
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/access_control/restriction_type/user/strategy/export/template/`;
      this.$http.get(url).then(
        (response) => {
          this.downloadYaml(response);
        },
        (errRes) => {
          if (errRes.status === 400) {
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('获取yaml模板失败')}，${errorMsg}`,
            });
          }
        }
      );
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
      const D = time.getDate() < 10 ? `0${time.getDate()}` : time.getDate();
      const h = `${time.getHours() < 10 ? `0${time.getHours()}` : time.getHours()}:`;
      const m = `${time.getMinutes() < 10 ? `0${time.getMinutes()}` : time.getMinutes()}:`;
      const s = time.getSeconds() < 10 ? `0${time.getSeconds()}` : time.getSeconds();
      return `${Y + M + D} ${h}${m}${s}`;
    },

    authDetailTimeHandler(e) {
      if (e.target.value === '') {
        const currentTimestampNow = new Date().getTime();
        const nowDate = this.timestampToTime(currentTimestampNow + 24 * 3600 * 1000);
        this.curUserParams.expires_at = nowDate;

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
      this.curUserParams.expires_at = date;

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

    handleRenewal(row) {
      this.renewalDialog.id = row.id;
      this.renewalDialog.visiable = true;
    },

    sortTab() {
      if (!this.pagination.count) {
        return;
      }
      this.is_up = !this.is_up;
      this.pagination.current = 1;
      this.pagination.limit = 10;
      this.fetchUserPermissionList(true);
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
        ]
      );
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
      this.fetchUserPermissionList(true);
    },

    batchDelete() {
      if (this.currentSelectList.length === 1) {
        const { id } = this.currentSelectList[0];
        this.curUserParams = this.currentSelectList[0];
        this.removeUserDialog.id = id;
        this.removeUserDialog.visiable = true;
        return;
      }
      this.batchRemoveUserDialog.visiable = true;
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
      this.fetchUserPermissionList(true);
    },

    searchUserPermissionList() {
      if (this.keyword === '') {
        return;
      }
      this.isFilter = true;
      this.pagination.limit = 10;
      this.pagination.current = 1;
      this.fetchUserPermissionList(true);
    },

    afterAddClose() {
      this.renewalDialog.id = 0;
      this.addUserDialog.showForm = false;
      this.addUserDialog.isEdit = false;
      this.addUserDialog.title = this.$t('添加用户白名单');
      this.curUserParams.content = '';
      this.rtxList = [];
      this.curUserParams.desc = '';
      this.curUserParams.expires_at = null;
      this.setTimeFilters();
      this.customTime = 1;
    },

    afterRenewalClose() {
      this.renewalDialog.id = 0;
      this.curUserParams.content = '';
      this.curUserParams.desc = '';
      this.curUserParams.expires_at = null;
      this.renewalParams.expires_at = null;
      this.renewalParams.expires = '';
      this.setTimeFilters();
      this.customTime = 1;
    },

    clearKeyword() {
      this.keyword = '';
    },

    updateCurUserContent(rtxList) {
      // 人员选择器的返回值为list，为了与接口匹配，用;拼接
      this.curUserParams.content = rtxList.join(';');
    },

    togglePermission() {
      this.userPermissionDialog.visiable = !this.userPermissionDialog.visiable;
    },

    handleEdit(row) {
      const { content, desc, expires_at, id } = row;
      this.curUserParams = Object.assign(
        {},
        {
          content,
          desc,
          expires_at,
        }
      );
      if (this.userType === 'rtx') {
        this.rtxList = content.split(';');
      }
      this.renewalDialog.id = id;
      this.addUserDialog.title = this.$t('编辑用户白名单');
      this.addUserDialog.visiable = true;
      this.addUserDialog.showForm = true;
      this.addUserDialog.isEdit = true;
    },

    showUserModal() {
      // 清空RTX输入框
      this.rtxList = [];
      this.addUserDialog.title = this.$t('添加用户白名单');
      this.addUserDialog.visiable = true;
      this.addUserDialog.showForm = true;
    },

    handlerAllChange(selection) {
      this.currentSelectList = [...selection];
    },

    handlerChange(selection) {
      this.currentSelectList = [...selection];
    },

    showRemoveModal(user) {
      this.curUserParams = user;
      this.removeUserDialog.visiable = true;
      this.removeUserDialog.id = user.id;
    },

    async setUserType() {
      const { region } = this.curAppInfo.application;
      const res = await this.$store.dispatch('fetchRegionInfo', region);
      this.userType = res.access_control ? res.access_control.user_type : 'qq';
    },

    async setUserPermission() {
      this.userPermissionDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/setUserPermissin', {
          appCode: this.appCode,
          is_enabled: !this.isUseUserPermission,
        });
        this.isUseUserPermission = !this.isUseUserPermission;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail,
        });
      } finally {
        this.userPermissionDialog.isLoading = false;
        this.closePermission();
      }
    },

    closePermission() {
      this.userPermissionDialog.visiable = false;
    },

    async checkUserPermissin() {
      this.isPermissionChecking = true;
      try {
        const res = await this.$store.dispatch('user/checkUserPermissin', {
          appCode: this.appCode,
        });
        this.isUseUserPermission = res.is_enabled;
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

    async fetchUserPermissionList(isTableLoading = false) {
      this.tableLoading = isTableLoading;
      try {
        const params = {
          appCode: this.appCode,
          limit: this.pagination.limit,
          offset: (this.pagination.current - 1) * this.pagination.limit,
          order_by: this.is_up ? '-created' : 'created',
          search_term: this.keyword,
        };

        const res = await this.$store.dispatch('user/getUserPermissionList', params);
        this.pagination.count = res.count;
        this.userPermissionList.splice(0, this.userPermissionList.length, ...(res.results || []));
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (e) {
        this.tableEmptyConf.isAbnormal = true;
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('获取白名单失败：')} ${e.detail}`,
        });
      } finally {
        if (isTableLoading) {
          this.tableLoading = false;
        }
      }
    },

    checkUserParams(params) {
      // qq regexp
      const qqRegexp = /^[1-9][0-9]{4,14}$/;
      const { userType } = this;
      const text = this.addUserDialog.isEdit ? this.$t('编辑用户') : this.$t('新增用户');
      if (!params.content) {
        this.$paasMessage({
          theme: 'error',
          message: `${text}${this.$t('失败：')} ${this.$t('请输入')}${this.userTypeMap[userType]}！`,
        });
        return false;
      }

      if (userType === 'qq') {
        const checkList = params.content
          .trim()
          .split(';')
          .filter((item) => item !== '');
        for (const item of checkList) {
          if (!qqRegexp.test(item)) {
            this.$paasMessage({
              theme: 'error',
              message: `${text}${this.$t('失败：')} ${this.$t('请输入合法的QQ！')}`,
            });
            return false;
          }
        }
      }

      if (!params.desc) {
        this.$paasMessage({
          theme: 'error',
          message: `${text}${this.$t('失败：')} ${this.$t('请输入添加原因！')}`,
        });
        return false;
      }

      return true;
    },

    addUser() {
      const params = this.curUserParams;

      this.addUserDialog.isLoading = true;
      setTimeout(() => {
        this.$refs.addUserForm.validate().then(
          () => {
            if (this.checkUserParams(params)) {
              this.submitUserParams();
            } else {
              this.addUserDialog.isLoading = false;
            }
          },
          () => {
            this.addUserDialog.isLoading = false;
          }
        );
      }, 200);
    },

    submitUserParams() {
      if (this.addUserDialog.isEdit) {
        this.handleEditUser();
      } else {
        this.handleAddUser();
      }
    },

    async handleAddUser() {
      const params = JSON.parse(JSON.stringify(this.curUserParams));
      params.content = params.content
        .trim()
        .split(';')
        .filter((item) => item !== '')
        .join(';');
      this.addUserDialog.isLoading = true;
      try {
        const res = await this.$store.dispatch('user/addUser', {
          appCode: this.appCode,
          params,
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.fetchUserPermissionList(true);
        const { added, ignored } = res;
        let message = '';
        if (added.length && ignored.length) {
          message = res.ignored.length
            ? `${this.$t('用户')}(${ignored.join('，')})${this.$t('已经存在，其余')} ${added.length} ${this.$t(
                '个用户已添加成功'
              )}`
            : '';
        } else if (!added.length && ignored.length) {
          message = this.$t('用户都已经在白名单中，请勿重复添加');
        } else {
          message = this.$t('添加成功');
        }
        this.$paasMessage({
          theme: 'success',
          message,
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('`添加失败： ')}${e.detail}`,
        });
      } finally {
        this.addUserDialog.isLoading = false;
        this.cancelAddUser();
      }
    },

    async handleEditUser() {
      this.addUserDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/userPermissinRenewal', {
          appCode: this.appCode,
          id: this.renewalDialog.id,
          params: this.curUserParams,
        });
        this.fetchUserPermissionList(true);
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
        this.addUserDialog.isLoading = false;
        this.cancelAddUser();
      }
    },

    async handleRenewalDialog() {
      this.renewalDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/userPermissinRenewal', {
          appCode: this.appCode,
          id: this.renewalDialog.id,
          params: this.renewalParams,
        });
        this.currentSelectList = [];
        this.fetchUserPermissionList(true);
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

    async batchRemoveUser() {
      this.batchRemoveUserDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/deleteUserPermission', {
          appCode: this.appCode,
          ids: this.currentSelectList.map((item) => item.id),
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchUserPermissionList(true);
        this.$paasMessage({
          theme: 'success',
          message: this.$t('批量删除成功'),
        });
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: `${this.$t('批量删除失败：')} ${e.detail}`,
        });
      } finally {
        this.batchRemoveUserDialog.isLoading = false;
        this.batchRemoveUserDialog.visiable = false;
      }
    },

    async removeUser() {
      this.removeUserDialog.isLoading = true;
      try {
        await this.$store.dispatch('user/deleteUserPermission', {
          appCode: this.appCode,
          ids: [this.removeUserDialog.id],
        });
        this.pagination.current = 1;
        this.pagination.limit = 10;
        this.currentSelectList = [];
        this.fetchUserPermissionList(true);
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
        this.removeUserDialog.isLoading = false;
        this.removeUserDialog.visiable = false;
      }
    },

    afterCloseRemove() {
      this.curUserParams = JSON.parse(
        JSON.stringify({
          content: '',
          desc: '',
          expires_at: null,
        })
      );
      this.removeUserDialog.id = 0;
    },

    cancelAddUser() {
      this.addUserDialog.visiable = false;
    },

    setTimeFilters() {
      this.timeFilters = Object.assign(
        {},
        {
          month: this.$t('1个月'),
          month3: this.$t('3个月'),
          month6: this.$t('6个月'),
          month12: this.$t('12个月'),
          forever: this.$t('永久'),
          custom: this.$t('自定义'),
          cur: 'forever',
        }
      );
      if (this.isExternal) {
        this.$delete(this.timeFilters, 'forever');
        this.timeFilters.cur = 'month6';
      }
    },

    async init() {
      this.$refs.moduleRef && this.$refs.moduleRef.setCurModule(this.curModule);
      this.setTimeFilters();
      await this.setUserType();
      this.checkUserPermissin();
      this.fetchUserPermissionList();
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
.access-user {
  min-height: calc(100% - 50px);
  padding: 20px 24px;
}
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

  .perm-icon {
    float: left;
    width: 42px;
    height: 42px;
    background: rgba(195, 205, 215, 1);
    border-radius: 2px;
    color: #fff;
    margin-right: 12px;
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
    .perm-status {
      border-radius: 2px;
      height: 22px;
      text-align: center;
      line-height: 22px;
      margin-left: 15px;
      font-size: 12px;
      padding: 0 5px;
    }
    .perm-status-open {
      color: #14a568;
      background: #e4faf0;
    }
    .perm-status-close {
      color: #fff;
      background-color: #dcdee5;
    }
  }

  .perm-tip {
    font-size: 12px;
    line-height: 1;
    font-size: 12px;
    color: #979ba5;
    .a-link {
      margin-left: 5px;
      &:hover {
        color: #699df4;
      }
    }
  }
}

.container {
  width: 100%;
  padding: 20px 0;
  color: #666;
}

.table-container {
  background: #fff;
  padding: 0px 0px 20px;
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

.middle {
  border-bottom: none;
  padding-top: 10px;
}

.reason {
  max-width: 150px;
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

.by-user-export-wrapper {
  height: auto !important;
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

.user-tab-cls {
  background: #fff;
  margin-top: 10px;
  /deep/ .bk-tab-section {
    padding: 0 !important;
  }
}
</style>
