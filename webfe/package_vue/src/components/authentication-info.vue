<template>
  <div v-if="canViewSecret" class="basic-info-item">
    <div class="title">
      {{ $t('鉴权信息') }}
    </div>
    <div class="info">
      {{ $t('在调用蓝鲸云 API 时需要提供应用鉴权信息。使用方法请参考：') }}
      <a :href="GLOBAL.DOC.APIGW_USER_API" target="_blank">
        {{ $t('API调用指引') }}
      </a>
    </div>
    <!-- 新增密钥 -->
    <div class="addSecret">
      <bk-popconfirm
        width="240"
        trigger="click"
        placement="bottom-start"
        :confirm-button-is-text="true"
        :cancel-button-is-text="true"
        @confirm="confirmAddSecret"
      >
        <a v-bk-tooltips.light="addTooltipsConfig" class="bk-text-default mr15" :disabled="appSecretList.length === 1">
          <bk-button theme="primary" icon="plus" class="mr10" :disabled="!(appSecretList.length === 1)">
            {{ $t('新增密钥') }}
          </bk-button>
        </a>
        <div slot="content">
          <div class="add-content-text">
            {{ $t('新建后，已有密钥的状态保持不变') }}
          </div>
        </div>
      </bk-popconfirm>
    </div>

    <!-- 密钥列表 -->
    <div class="secrectList">
      <bk-table :data="appSecretList" size="medium">
        <bk-table-column :label="$t('应用 ID （bk_app_code）')" prop="bk_app_code" width="190"></bk-table-column>
        <bk-table-column :label="$t('应用密钥 (bk_app_secret)')" width="315">
          <template slot-scope="props">
            <span>{{ props.row.bk_app_secret }}&nbsp;</span>
            <span
              v-if="isView(props.row.bk_app_secret)"
              v-bk-tooltips="platformFeature.VERIFICATION_CODE ? $t('验证查看') : $t('点击查看')"
              class="paasng-icon paasng-eye-slash icon-color"
              style="cursor: pointer"
              @click="getSecretDetail(props.row)"
            />
            <span
              v-else
              class="paasng-icon paasng-general-copy icon-color copy"
              style="cursor: pointer"
              @click="copySecretText"
              :data-clipboard-text="props.row.bk_app_secret"
            />
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('创建时间')" prop="created_at"> </bk-table-column>
        <bk-table-column :label="$t('状态')">
          <template slot-scope="props">
            <span :style="{ color: props.row.enabled ? '#2DCB56' : '#FF5656' }">
              {{ props.row.enabled ? $t('已启用') : $t('已禁用') }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('操作')">
          <template slot-scope="props">
            <a
              v-bk-tooltips.light="disabledTooltipsConfig"
              :disabled="!isDefault(props.row.bk_app_secret)"
              class="bk-text-default mr15"
            >
              <bk-button class="mr10" text :disabled="isDefault(props.row.bk_app_secret)" @click="isEnabled(props.row)">
                {{ props.row.enabled ? $t('禁用') : $t('启用') }}
              </bk-button>
            </a>
            <bk-button v-if="!props.row.enabled" class="mr10" theme="primary" text @click="deleteSecret(props.row)">
              {{ $t('删除') }}</bk-button
            >
          </template>
        </bk-table-column>
      </bk-table>
    </div>

    <!-- 环境变量默认密钥 -->
    <div class="defaultSecret" v-if="defaultSecret !== undefined">
      <div class="title mr">{{ $t('环境变量默认密钥') }}</div>
      <div class="info">
        {{ $t('内置环境变量 BKPAAS_APP_SECRET 使用的密钥。') }}
        <a :href="GLOBAL.DOC.ENV_VAR_INLINE" target="_blank">
          {{ $t('文档：什么是内置环境变量') }}
        </a>
      </div>
      <div class="defaultSecretCode">
        <label class="title-label"> BKPAAS_APP_SECRET：&emsp;</label>
        <span class="defaultext"> {{ appSecret ? appSecret : defaultSecret }}&nbsp; </span>
        <span
          v-if="!appSecret"
          v-bk-tooltips="platformFeature.VERIFICATION_CODE ? $t('验证查看') : $t('点击查看')"
          class="paasng-icon paasng-eye-slash icon-color"
          style="cursor: pointer"
          @click="onSecretToggle"
        />
        <span
          v-if="appSecret"
          class="paasng-icon paasng-general-copy icon-color copy"
          style="cursor: pointer"
          @click="copySecretText"
          :data-clipboard-text="appSecret"
        />
      </div>

      <!-- 已部署密钥概览 -->
      <div class="deployedSecret" v-if="!isSameSecrect">
        <div class="info mb">{{ $t('已部署密钥概览：') }}</div>
        <bk-table :data="DeployedSecret" border>
          <bk-table-column :label="$t('模块')" prop="module" width="160"></bk-table-column>
          <bk-table-column :label="$t('环境')" class-name="table-colum-cls" width="200">
            <template slot-scope="props">
              <div class="container">
                <div
                  v-for="item in props.row.data"
                  :key="item.latest_deployed_at"
                  style="height: 40px; line-height: 40px"
                  class="container-child"
                >
                  <div class="ml15">{{ $t(entryEnv[item.environment]) }}</div>
                </div>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('最近部署时间')" class-name="table-colum-cls" width="200">
            <template slot-scope="props">
              <div class="container">
                <div
                  v-for="item in props.row.data"
                  :key="item.latest_deployed_at"
                  style="height: 40px; line-height: 40px"
                  class="container-child"
                >
                  <div class="ml15">
                    {{ smartTime(item.latest_deployed_at, 'fromNow') }}
                  </div>
                </div>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('BKPAAS_APP_SECRET')" class-name="table-colum-cls">
            <template slot-scope="props">
              <div class="container">
                <div v-for="item in props.row.data" :key="item.latest_deployed_at" class="container-child">
                  <div class="ml15 normalSecret" v-if="item.bk_app_secret === defaultSecret">
                    {{ item.bk_app_secret }}
                  </div>
                  <div class="diffSecret" v-else>
                    <div class="ml15 mr15 flexText">
                      <div class="appSecretText">{{ item.bk_app_secret }}</div>
                      <div class="errorText info-circle-color">
                        <bk-icon type="info-circle" class="info-circle-color" />
                        {{ $t('与默认密钥不一致，') }}
                        <bk-button theme="primary" text @click="handleDeploy(item)">
                          {{ $t('部署以更新密钥') }}
                        </bk-button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </bk-table-column>
        </bk-table>
      </div>

      <!-- 更换默认密钥按钮 -->
      <div class="changeDefaultSecret">
        <bk-button theme="primary" class="mr10" @click="clickChangeDefault">
          {{ $t('更换默认密钥') }}
        </bk-button>
      </div>
    </div>

    <!-- 禁用密钥对话框 -->
    <bk-dialog
      width="443"
      v-model="disabledVisible"
      :mask-close="false"
      :ok-text="$t('禁用')"
      :title="$t('禁用密钥')"
      header-position="left"
      @confirm="confirmDisabled"
    >
      {{ $t('禁用此密钥后，蓝鲸云 API 将拒绝此密钥的所有请求。禁用后，预计 15 分钟内生效。') }}
    </bk-dialog>

    <!-- 删除密钥对话框 -->
    <bk-dialog
      width="475"
      v-model="deleteVisible"
      :mask-close="false"
      :title="$t('删除密钥')"
      header-position="left"
      @confirm="confirmDeleteSecret"
      @cancel="cancelDelete"
    >
      <bk-alert type="error" :title="$t('删除此密钥后无法再恢复，蓝鲸云 API 将永久拒绝此密钥的所有请求。')"></bk-alert>
      <bk-form :label-width="427" form-type="vertical" :model="deleteFormData">
        <bk-form-item>
          {{ $t('请完整输入') }} &nbsp;
          <span style="color: #ff56f5">
            {{ curAppInfo.application.code }}
          </span>
          &nbsp;{{ $t('来确认删除密钥！') }}
          <bk-input
            :placeholder="curAppInfo.application.code"
            style="margin-bottom: 15px"
            v-model="deleteFormData.verifyText"
          />
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 更换默认密钥对话框 -->
    <bk-dialog
      width="475"
      v-model="changeDefaultVisible"
      :mask-close="false"
      :title="$t('更换默认密钥')"
      header-position="left"
      @confirm="confirmchangeDefault"
    >
      {{ $t('请选择密钥（只能选择已启用的密钥）：') }}
      <bk-select v-model="curSelect" class="secretSelect">
        <bk-option
          v-for="option in optionSecretList"
          :key="option.id"
          :id="option.bk_app_secret"
          :name="option.bk_app_secret"
          :disabled="!option.enabled"
          v-bind="option"
        >
          <span>{{ option.bk_app_secret }}</span>
          <span>{{ option.enabled ? $t(' (创建时间:') : $t(' (已禁用') }}</span>
          <span v-if="option.enabled">
            {{ smartTime(option.created_at, 'smartShorten') }}
          </span>
          <span>)</span>
        </bk-option>
        <div
          slot="extension"
          @click="confirmAddSecret"
          style="cursor: pointer; text-align: center"
          v-if="appSecretList.length === 1"
        >
          <i class="bk-icon icon-plus-circle"></i> {{ $t('新增密钥') }}
        </div>
      </bk-select>

      <bk-alert type="info" :title="$t('密钥更换后，需要重新部署才能生效！')"></bk-alert>
    </bk-dialog>

    <!-- 验证码对话框 -->
    <bk-dialog v-model="verifyVisible" width="475" :ok-text="$t('提交')" @cancel="cancelSend" @confirm="confirmSend">
      <p>{{ $t('验证码已发送至您的企业微信，请注意查收！') }}</p>
      <p style="display: flex; align-items: center" class="mt15">
        <b> {{ $t('验证码：') }} </b>
        <bk-input
          v-model="appSecretVerificationCode"
          type="text"
          :placeholder="$t('请输入验证码')"
          style="width: 200px; margin-right: 10px"
        />
        <bk-button v-if="appSecretTimer !== 0" theme="default" :disabled="true">
          {{ appSecretTimer }}s&nbsp;{{ $t('后重新获取') }}
        </bk-button>
        <bk-button v-else theme="default" @click="sendMsg">
          {{ $t('重新获取') }}
        </bk-button>
      </p>
    </bk-dialog>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import { ENV_ENUM } from '@/common/constants';
import _ from 'lodash';
export default {
  mixins: [appBaseMixin],
  data() {
    return {
      verifyVisible: false,
      appSecretVerificationCode: '',
      appSecretTimer: 0,
      appSecret: null,
      appSecretList: [],
      addTooltipsConfig: {
        content: this.$t('密钥已达到上限，应用仅允许有 2 个密钥'),
        placement: 'right',
        theme: 'light',
      },
      disabledTooltipsConfig: {
        content: this.$t('当前密钥为环境变量默认密钥，不允许禁用'),
        placement: 'right',
        theme: 'light',
      },
      defaultSecret: '',
      disabledVisible: false,
      deleteVisible: false,
      deleteFormData: {
        verifyText: '',
      },
      curSecret: {},
      DeployedSecret: [],
      entryEnv: ENV_ENUM,
      changeDefaultVisible: false,
      curSelect: '',
      originDeployedSecret: [],
      optionSecretList: [],
      viewStatus: {},
    };
  },
  computed: {
    canViewSecret() {
      return this.curAppInfo.role && this.curAppInfo.role.name !== 'operator';
    },
    platformFeature() {
      console.warn(this.$store.state.platformFeature);
      return this.$store.state.platformFeature;
    },
    userFeature() {
      return this.$store.state.userFeature;
    },
    // 部署密钥和默认密钥是否一致
    isSameSecrect() {
      if (this.originDeployedSecret.length !== 0) {
        const isNull = this.originDeployedSecret.some(item => item.bk_app_secret === null);
        if (isNull) {
          return true;
        }
        return this.originDeployedSecret.every(item => item.bk_app_secret === this.defaultSecret);
      }
      return true;
    },
    // 是否查看
    isView() {
      return function (code) {
        return code.includes('*');
      };
    },
    // 是否是默认密钥
    isDefault() {
      return function (code) {
        if (!this.defaultSecret) {
          return false;
        }
        const startFlag = code.substring(0, 4) === this.defaultSecret.substring(0, 4);
        const endFlag = code.substring(code.length - 4) === this.defaultSecret.substring(this.defaultSecret.length - 4);
        return startFlag && endFlag;
      };
    },
  },
  watch: {
    'curAppInfo.application.code': {
      handler(newValue) {
        console.log(newValue);
        this.getSecretList();
        this.getDefaultSecret();
        this.getDeployedSecret();
      },
      deep: true,
    },
  },
  mounted() {
    this.getSecretList();
    this.getDefaultSecret();
    this.getDeployedSecret();
  },
  methods: {
    onSecretToggle() {
      if (!this.userFeature.VERIFICATION_CODE) {
        const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
        this.$http.post(url, { verification_code: '' }).then(
          (res) => {
            console.log('res--appSecret', res);
            this.appSecret = res.app_secret;
          },
          () => {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('验证码错误！'),
            });
          },
        );
        return;
      }
      this.verifyVisible = true;
      this.sendMsg()
        .then(() => {
          this.verifyVisible = true;
        })
        .catch(() => {
          this.verifyVisible = false;
          this.appSecretTimer = 0;
          this.$paasMessage({
            theme: 'error',
            message: this.$t('请求失败，请稍候重试'),
          });
        });
    },
    getAppSecret() {
      if (this.appSecretVerificationCode === '') {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: this.$t('请输入验证码！'),
        });
        return;
      }
      const form = {
        verification_code: this.appSecretVerificationCode,
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verifications/`;
      this.$http
        .post(url, form)
        .then(
          (res) => {
            this.appSecret = res.app_secret;
          },
          () => {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('验证码错误！'),
            });
          },
        )
        .then(() => {
          this.appSecretVerificationCode = '';
        });
    },
    sendMsg() {
      // 硬编码，需前后端统一
      return new Promise((resolve, reject) => {
        this.resolveLocker = resolve;
        if (this.appSecretTimer > 0) {
          this.resolveLocker();
          return;
        }
        const url = `${BACKEND_URL}/api/accounts/verification/generation/`;

        this.appSecretTimer = 60;
        this.$http.post(url, { func: 'GET_APP_SECRET' }).then(
          () => {
            this.appSecretVerificationCode = '';
            this.resolveLocker();
            if (!this.appSecretTimeInterval) {
              this.appSecretTimeInterval = setInterval(() => {
                if (this.appSecretTimer > 0) {
                  // eslint-disable-next-line no-plusplus
                  this.appSecretTimer--;
                } else {
                  clearInterval(this.appSecretTimeInterval);
                  this.appSecretTimeInterval = undefined;
                }
              }, 1000);
            }
          },
          () => {
            this.appSecretVerificationCode = '';
            reject(new Error(this.$t('请求失败，请稍候重试！')));
          },
        );
      });
    },
    resetAppSecret() {
      this.appSecret = null;
      this.showingSecret = false;
      this.appSecretTimer = 0;
    },
    // 获取单个密钥详情
    getSecretDetail(status) {
      if (this.userFeature.VERIFICATION_CODE) {
        this.viewStatus = status;
        this.sendMsg()
          .then(() => {
            this.verifyVisible = true;
          })
          .catch(() => {
            this.verifyVisible = false;
            this.appSecretTimer = 0;
            this.$paasMessage({
              theme: 'error',
              message: this.$t('请求失败，请稍候重试'),
            });
          });
        return;
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verification/${status.id}/`;
      this.$http.post(url).then((res) => {
        this.appSecretList.forEach((item) => {
          if (item.id === status.id) {
            // eslint-disable-next-line no-param-reassign
            item.bk_app_secret = res.bk_app_secret;
            return;
          }
        });
      });
    },
    // 复制密钥文本
    copySecretText() {
      // eslint-disable-next-line no-undef
      const clipboard = new Clipboard('.copy');
      clipboard.on('success', () => {
        clipboard.destroy();
      });
      clipboard.on('error', () => {
        this.$bkMessage({
          message: '该浏览器不支持复制',
          offsetY: 80,
          theme: 'error',
        });
        clipboard.destroy();
      });
    },
    // 确认提交验证码
    confirmSend() {
      if (JSON.stringify(this.viewStatus) === '{}') {
        this.getAppSecret();
        return;
      }
      if (this.appSecretVerificationCode === '') {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: this.$t('请输入验证码！'),
        });
        return;
      }
      const form = {
        verification_code: this.appSecretVerificationCode,
      };
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secret_verification/${this.viewStatus.id}/`;
      this.$http
        .post(url, form)
        .then(
          (res) => {
            this.appSecretList.forEach((item) => {
              if (item.id === this.viewStatus.id) {
                // eslint-disable-next-line no-param-reassign
                item.bk_app_secret = res.bk_app_secret;
                return;
              }
            });
          },
          () => {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('验证码错误！'),
            });
          },
        )
        .then(() => {
          this.appSecretVerificationCode = '';
          this.viewStatus = {};
        });
    },
    // 取消提交验证码
    cancelSend() {
      this.appSecretVerificationCode = '';
    },
    // 确认新增密钥
    confirmAddSecret() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secrets/`;
      this.$http
        .post(url)
        .then(() => {})
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('接口异常'),
          });
        })
        .finally(() => {
          this.getSecretList();
        });
    },
    // 获取密钥列表
    getSecretList() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secrets/`;
      this.$http
        .get(url)
        .then((res) => {
          this.appSecretList = res;
          this.optionSecretList = _.cloneDeep(res);
        })
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('接口异常'),
          });
        });
    },
    // 调用启用或禁用的接口
    isEnabledApi(status) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secrets/${status.id}/`;
      this.$http
        .post(url, { enabled: !status.enabled })
        .then(() => {})
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('接口异常'),
          });
        })
        .finally(() => {
          this.getSecretList();
        });
    },
    // 启用/禁用密钥
    isEnabled(status) {
      this.curSecret = status;
      if (status.enabled) {
        this.disabledVisible = true;
        return;
      }
      this.isEnabledApi(status);
    },
    // 确认禁用密钥
    confirmDisabled() {
      this.isEnabledApi(this.curSecret);
    },
    // 删除密钥
    deleteSecret(status) {
      this.curSecret = status;
      this.deleteVisible = true;
    },
    // 确认删除
    confirmDeleteSecret() {
      const verifyText = this.deleteFormData.verifyText.trim();
      const curText = this.curAppInfo.application.code;
      if (verifyText !== curText) {
        this.$bkMessage({
          message: this.$t('输入有误，请重新输入'),
          offsetY: 80,
          theme: 'error',
        });
        this.deleteFormData.verifyText = '';
        return;
      }
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/secrets/${this.curSecret.id}/`;
      this.$http
        .delete(url)
        .then(() => {})
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('删除失败，请重新操作'),
          });
        })
        .finally(() => {
          this.getSecretList();
          this.deleteFormData.verifyText = '';
        });
    },
    // 取消删除
    cancelDelete() {
      this.deleteFormData.verifyText = '';
    },
    // 获取环境变量默认密钥
    getDefaultSecret() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/default_secret/`;
      this.$http
        .get(url)
        .then((res) => {
          this.defaultSecret = res.app_secret_in_config_var;
          this.curSelect = res.app_secret_in_config_var;
        })
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('接口异常'),
          });
        })
        .finally(() => {
          this.getSecretList();
        });
    },
    // 获取已部署密钥概览
    getDeployedSecret() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/deployed_secret/`;
      this.$http
        .get(url)
        .then((res) => {
          this.originDeployedSecret = res;
          const formatRes = res.reduce((arr, obj) => {
            const foundIndex = arr.findIndex(item => item.module === obj.module);
            if (foundIndex !== -1) {
              arr[foundIndex].data.unshift(obj);
            } else {
              arr.push({
                module: obj.module,
                data: [obj],
              });
            }
            return arr;
          }, []);
          console.log(formatRes);
          this.DeployedSecret = formatRes;
        })
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('接口异常'),
          });
        });
    },
    // 点击按钮更换默认密钥
    clickChangeDefault() {
      this.changeDefaultVisible = true;
      this.curSelect = this.defaultSecret;
    },
    // 更换默认密钥
    changeDefaultsSecret(id) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.curAppInfo.application.code}/default_secret/`;
      this.$http
        .post(url, { id })
        .then(() => {})
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('更换失败，请重新操作'),
          });
        })
        .finally(() => {
          this.getDefaultSecret();
        });
    },
    // 确认更换密钥
    confirmchangeDefault() {
      const cur = this.optionSecretList.find(item => item.bk_app_secret === this.curSelect);
      this.changeDefaultsSecret(cur.id);
      this.appSecret = null;
    },
    // 部署更新密钥
    handleDeploy(item) {
      const appRouterInfo =        item.environment === 'stag'
        ? {
          name: 'appDeploy',
          params: {
            id: this.curAppInfo.application.code,
            moduleId: item.module,
          },
        }
        : {
          name: 'appDeployForProd',
          params: {
            id: this.curAppInfo.application.code,
            moduleId: item.module,
          },
          query: {
            focus: 'prod',
          },
        };
      this.$router.push(appRouterInfo);
    },
  },
};
</script>

<style lang="scss" scoped>
.basic-info-item {
  margin-bottom: 35px;
  .title {
    color: #313238;
    font-size: 14px;
    font-weight: bold;
    line-height: 1;
    margin-bottom: 5px;
  }
  .info {
    color: #979ba5;
    font-size: 12px;
  }
  .addSecret {
    margin-top: 16px;
    margin-bottom: 16px;
  }
  .content {
    margin-top: 16px;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    &.no-border {
      border: none;
    }
    .info-special-form:nth-child(2) {
      position: relative;
      top: -4px;
    }
    .info-special-form:nth-child(3) {
      position: relative;
      top: -8px;
    }
    .info-special-form:nth-child(4) {
      position: relative;
      top: -12px;
    }
    .info-special-form:nth-child(5) {
      position: relative;
      top: -16px;
    }
    .item-content {
      padding: 0 10px 0 25px;
      height: 42px;
      line-height: 42px;
      border-right: 1px solid #dcdee5;
      border-bottom: 1px solid #dcdee5;
    }

    .item-logn-content {
      padding: 20px 10px 0 25px;
      height: 105px;
      border-right: 1px solid #dcdee5;
      border-top: 1px solid #dcdee5;
      .tip {
        font-size: 12px;
        color: #979ba5;
      }
    }
    .title-label {
      display: inline-block;
      width: 180px;
      height: 42px;
      line-height: 42px;
      text-align: center;
      border: 1px solid #dcdee5;
    }

    .logo {
      height: 105px;
      line-height: 105px;
    }

    .plugin-info {
      height: 460px;
      padding-top: 20px;
    }
    .content-item {
      position: relative;
      height: 60px;
      line-height: 60px;
      border-bottom: 1px solid #dcdee5;
      label {
        display: inline-block;
        position: relative;
        top: -1px;
        width: 180px;
        height: 60px;
        border-right: 1px solid #dcdee5;
        color: #313238;
        vertical-align: middle;
        .basic-p {
          padding-left: 30px;
        }
        .title-p {
          line-height: 30px;
          text-align: center;
          &.tip {
            font-size: 12px;
            color: #979ba5;
          }
        }
        .top {
          transform: translateY(5px);
        }
        .bottom {
          transform: translateY(-5px);
        }
      }
      .item-practical-content {
        display: inline-block;
        padding-left: 20px;
        max-width: calc(100% - 180px);
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
        vertical-align: top;

        .edit-input {
          display: inline-block;
          position: relative;
          top: -1px;
        }

        .edit-button {
          display: inline-block;
          position: absolute;
          right: 10px;
        }

        .edit {
          position: relative;
          color: #63656e;
          font-weight: bold;
          cursor: pointer;
          &:hover {
            color: #3a84ff;
          }
        }
      }
    }
    .content-item:last-child {
      border-bottom: none;
    }
    .pre-release-wrapper,
    .production-wrapper {
      display: inline-block;
      position: relative;
      width: 430px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      vertical-align: top;
      &.has-left {
        left: 12px;
      }
      .header {
        height: 41px;
        line-height: 41px;
        border-bottom: 1px solid #dcdee5;
        background: #fafbfd;
        .header-title {
          margin-left: 20px;
          color: #63656e;
          font-weight: bold;
          float: left;
        }
        .switcher-wrapper {
          margin-right: 20px;
          float: right;
          .date-tip {
            margin-right: 5px;
            line-height: 1;
            color: #979ba5;
            font-size: 12px;
          }
        }
      }
      .ip-content {
        padding: 14px 24px 14px 14px;
        height: 138px;
        overflow-x: hidden;
        overflow-y: auto;
        .ip-item {
          display: inline-block;
          margin-left: 10px;
          vertical-align: middle;
        }
        .no-ip {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          text-align: center;
          font-size: 12px;
          color: #63656e;
          p:nth-child(2) {
            margin-top: 2px;
          }
        }
      }
    }
    .ip-tips {
      margin-top: 7px;
      color: #63656e;
      font-size: 12px;
      i {
        color: #ff9c01;
      }
    }
  }
  .defaultSecretCode {
    font-size: 14px;
    height: 62px;
    line-height: 62px;
    color: #63656e;
    .defaultext {
      color: #313238;
    }
  }
  .mr {
    margin-top: 35px;
  }
  .icon-color {
    color: #1768ef;
    font-size: 14px;
  }
  .changeDefaultSecret {
    margin-top: 16px;
    margin-bottom: 16px;
  }
  /deep/ .deployedSecret {
    .bk-table-body {
      .table-colum-cls {
        .cell {
          padding: 0 !important;
          height: 100% !important;
          .container {
            display: flex;
            flex-direction: column;
            justify-content: space-around;
            height: 100%;
            width: 100%;
            .container-child:nth-child(2) {
              border-top: 1px solid #dfe0e5;
            }
            .container-child {
              flex: 1;
            }
            .normalSecret {
              height: 100%;
              line-height: 40px;
            }
            .diffSecret {
              background-color: #ffeeed;
              height: 100%;
              width: 100%;
              .flexText {
                display: flex;
                justify-content: space-between;
                height: 100%;
                align-items: center;
              }
            }
          }
        }
      }
    }
  }
}
.accept-vcode {
  position: relative;
  top: -6px;
  margin-top: 15px;
  padding: 20px;
  background: #fff;
  box-shadow: 0 2px 4px #eee;
  border: 1px solid #eaeeee;
  color: #666;
  z-index: 1600;

  .bk-loading2 {
    display: inline-block;
  }

  b {
    color: #333;
  }

  p {
    line-height: 30px;
    padding-bottom: 10px;
  }

  .password-text {
    padding: 0 10px;
    margin-right: 10px;
    width: 204px;
    height: 34px;
    line-height: 34px;
    border-radius: 2px 0 0 2px;
    border: solid 1px #e1e6e7;
    font-size: 14px;
    transition: all 0.5s;
  }

  .password-text:focus {
    outline: none;
    border-color: #e1e6e7;
    box-shadow: 0 2px 4px #eee;
  }

  .password-wait {
    background: #ccc;
    color: #fff;
    display: inline-block;
  }

  .password-submit,
  .password-reset {
    margin: 10px 10px 0 0;
    width: 90px;
    height: 34px;
    line-height: 34px;
    border: solid 1px #3a84ff;
    font-size: 14px;
    font-weight: normal;
  }

  .password-reset {
    color: #ccc;
    background: #fff;
    border: solid 1px #ccc;
  }

  .password-reset:hover {
    background: #ccc;
    color: #fff;
  }

  .get-password:after {
    content: '';
    position: absolute;
    top: -10px;
    left: 147px;
    width: 16px;
    height: 10px;
    background: url(/static/images/user-icon2.png) no-repeat;
  }

  .immediately {
    margin-left: 10px;
    width: 90px;
    height: 36px;
    line-height: 36px;
    color: #fff;
    text-align: center;
    background: #3a84ff;
    font-weight: bold;
    border-radius: 2px;
    transition: all 0.5s;
  }

  .immediately:hover {
    background: #4e93d9;
  }

  .immediately img {
    position: relative;
    top: 10px;
    margin-right: 5px;
    vertical-align: top;
  }
}

.secret-icon {
  transform: translate(4px, -4px);
}
.bk-tooltip-content {
  .bk-popconfirm-content {
    padding: 4px;
    .popconfirm-content {
      .add-content-text {
        color: #63656e;
        margin-bottom: 15px;
      }
    }
  }
}
.bk-form-vertical {
  margin-top: 16px;
}
.mb {
  margin-bottom: 16px;
}
.secretSelect {
  margin: 10px 0 15px;
}
.info-circle-color {
  color: #ea3636;
}
</style>
