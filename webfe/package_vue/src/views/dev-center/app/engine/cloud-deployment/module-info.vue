<template>
  <div class="module-info-container">
    <div class="base-info-container" v-if="isV1alpha2">
      <div class="flex-row align-items-center">
        <span class="base-info-title">
          {{ $t('基本信息-title') }}
        </span>
        <div class="edit-container" @click="handleProcessNameEdit">
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>
      </div>
      <div class="form-detail mt20 pb20 border-b">
        <bk-form
          :model="buildData">
          <bk-form-item
            :label="$t('托管方式：')">
            <span class="form-text">{{ artifactType || '--' }}</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('镜像仓库：')">
            <span class="form-text">{{ buildData.image || '--' }}</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('镜像凭证：')">
            <span class="form-text">{{ buildData.imagePullPolicy || '--' }}</span>
          </bk-form-item>
        </bk-form>
      </div>
    </div>

    <!-- 部署限制 -->
    <div class="base-info-container" v-if="isV1alpha2">
      <div class="flex-row align-items-center mt20">
        <span class="base-info-title">
          {{ $t('部署限制') }}
        </span>
        <div class="edit-container" @click="handleProcessNameEdit">
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>

        <div class="info">
          {{ $t('开启部署权限控制，仅管理员可部署、下架该模块') }}
        </div>
      </div>
      <div class="form-detail mt20 pb20 border-b">
        <bk-form
          :model="buildData">
          <bk-form-item
            :label="$t('预发布环境：')">
            <div class="form-text">{{ deployLimit.stag ? $t('已开启') : $t('未开启') }}</div>
          </bk-form-item>
          <bk-form-item
            :label="$t('生产环境：')">
            <div class="form-text">{{ deployLimit.prod ? $t('已开启') : $t('未开启') }}</div>
          </bk-form-item>
        </bk-form>
      </div>

      <div class="form-edit mt20 pb20 border-b">
        <bk-checkbox-group v-model="demo1">
          <bk-checkbox :value="'value1'">{{ $t('预发布环境') }}</bk-checkbox>
          <bk-checkbox :value="'value2'">{{ $t('生产环境') }}</bk-checkbox>
        </bk-checkbox-group>
      </div>
    </div>

    <!-- 出口IP -->
    <div class="base-info ip-info-container" v-if="isV1alpha2">
      <div class="flex-row align-items-center mt20">
        <span class="base-info-title">
          {{ $t('出口IP') }}
        </span>
        <div class="edit-container" @click="handleProcessNameEdit">
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>

        <div class="info">
          {{ $t('如果模块环境需要访问设置了 IP 白名单的外部服务，你可以在这里获取应用的出口 IP 列表，以完成外部服务授权。') }}
        </div>
      </div>
      <div class="form-detail mt20 pb20">
        <bk-form
          :model="buildData">
          <bk-form-item
            :label="$t('预发布环境：')">
            <div class="form-text">{{ deployLimit.stag ? $t('已开启') : $t('未开启') }}</div>
          </bk-form-item>
          <bk-form-item
            :label="$t('生产环境：')">
            <div class="form-text">{{ deployLimit.prod ? $t('已开启') : $t('未开启') }}</div>
          </bk-form-item>
        </bk-form>
      </div>

      <div class="form-edit">
        <div class="content no-border">
          <div class="pre-release-wrapper">
            <div class="header">
              <div class="header-title">
                {{ $t('预发布环境') }}
              </div>
              <div class="switcher-wrapper">
                <span
                  v-if="gatewayInfos.stag.created !== 'Invalid date'
                    && gatewayInfos.stag.node_ip_addresses.length && !gatewayInfosStagLoading"
                  class="f12 date-tip"
                  @click="stopCapturing"
                >{{ gatewayInfos.stag.created + $t('已获取') }}</span>
                <bk-switcher
                  v-model="gatewayEnabled.stag"
                  :disabled="curStagDisabled"
                  @change="gatewayInfosHandler(...arguments, 'stag')"
                />
              </div>
            </div>
            <div
              class="ip-content"
              contenteditable="false"
            >
              <div
                v-if="gatewayInfos.stag.node_ip_addresses.length"
                class="copy-wrapper"
                :title="$t('复制')"
                @click="handleCopyIp('stag')"
              >
                <i class="paasng-icon paasng-general-copy" />
              </div>
              <template v-if="gatewayInfos.stag.node_ip_addresses.length">
                <div
                  v-for="(nodeIp, nodeIpIndex) of gatewayInfos.stag.node_ip_addresses"
                  :key="nodeIpIndex"
                  class="ip-item"
                >
                  {{ nodeIp.internal_ip_address }}
                </div>
              </template>
              <template v-else-if="!curAppModule.clusters.stag.feature_flags.ENABLE_EGRESS_IP">
                <div class="no-ip">
                  <p> {{ $t('该环境暂不支持获取出流量 IP 信息') }} </p>
                </div>
              </template>
              <template v-else>
                <div class="no-ip">
                  <p> {{ $t('暂未获取出流量 IP 列表') }} </p>
                  <p> {{ $t('如有需要请联系管理员获取') }} </p>
                </div>
              </template>
            </div>
          </div>
          <div class="production-wrapper has-left">
            <div class="header">
              <div class="header-title">
                {{ $t('生产环境') }}
              </div>
              <div class="switcher-wrapper">
                <span
                  v-if="gatewayInfos.prod.created !== 'Invalid date'
                    && gatewayInfos.prod.node_ip_addresses.length && !gatewayInfosProdLoading"
                  class="f12 date-tip"
                  @click="stopCapturing"
                >{{ gatewayInfos.prod.created + $t('已获取') }}</span>
                <bk-switcher
                  v-model="gatewayEnabled.prod"
                  :disabled="curProdDisabled"
                  @change="gatewayInfosHandler(...arguments, 'prod')"
                />
              </div>
            </div>
            <div
              class="ip-content"
              contenteditable="false"
            >
              <div
                v-if="gatewayInfos.prod.node_ip_addresses.length"
                class="copy-wrapper"
                :title="$t('复制')"
                @click="handleCopyIp('prod')"
              >
                <i class="paasng-icon paasng-general-copy" />
              </div>
              <template v-if="gatewayInfos.prod.node_ip_addresses.length">
                <div
                  v-for="(nodeIp, nodeIpIndex) of gatewayInfos.prod.node_ip_addresses"
                  :key="nodeIpIndex"
                  class="ip-item"
                >
                  {{ nodeIp.internal_ip_address }}
                </div>
              </template>
              <template v-else-if="!curAppModule.clusters.prod.feature_flags.ENABLE_EGRESS_IP">
                <div class="no-ip">
                  <p> {{ $t('该环境暂不支持获取出流量 IP 信息') }} </p>
                </div>
              </template>
              <template v-else>
                <div class="no-ip">
                  <p> {{ $t('暂未获取出流量 IP 列表') }} </p>
                  <p> {{ $t('如有需要请联系管理员获取') }} </p>
                </div>
              </template>
            </div>
          </div>
          <div class="ip-tips">
            <i class="paasng-icon paasng-info-circle" />
            {{ $t('注意：重复获取列表可能会获得不一样的结果，请及时刷新外部服务白名单列表') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>import appBaseMixin from '@/mixins/app-base-mixin';
import moment from 'moment';
import _ from 'lodash';
export default {
  mixins: [appBaseMixin],
  props: {
    cloudAppData: {
      type: Object,
      default: {},
    },
  },
  data() {
    return {
      isLoading: false,
      buildData: {},
      localCloudAppData: {},
      deployLimit: {},
      gatewayInfos: {
        stag: {
          created: '',
          node_ip_addresses: [],
        },
        prod: {
          created: '',
          node_ip_addresses: [],
        },
      },
      gatewayEnabled: {
        stag: false,
        prod: false,
      },
    };
  },
  computed: {
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    isV1alpha2() {
      return this.localCloudAppData?.apiVersion?.includes('v1alpha2');
    },
    artifactType() {
      console.log('this.curAppModule.web_config', this.curAppModule.web_config);
      if (this.curAppModule.web_config.artifact_type === 'image') {
        if (this.curAppModule.web_config.build_method === 'custom_image') {
          return this.$t('仅镜像');
        }
        return this.$t('源码&镜像');
      }
      if (this.curAppModule.web_config.artifact_type === 'slug') {
        return this.$t('仅源码');
      }
      return '--';
    },

    curStagDisabled() {
      // 测试环境，没有启用 egress 的，也不再允许用户自己启用
      return this.gatewayInfosStagLoading
      || this.isGatewayInfosBeClearing
      || !this.gatewayInfos.stag.node_ip_addresses.length
      || !this.curAppModule.clusters.stag.feature_flags.ENABLE_EGRESS_IP;
    },

    curProdDisabled() {
      // 正式环境，没有启用 egress 的，也不再允许用户自己启用
      return this.gatewayInfosProdLoading
      || this.isGatewayInfosBeClearing
      || !this.gatewayInfos.prod.node_ip_addresses.length
      || !this.curAppModule.clusters.prod.feature_flags.ENABLE_EGRESS_IP;
    },
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData = _.cloneDeep(val);
          this.buildData = this.localCloudAppData.spec.build || {};
        }
      },
      immediate: true,
      deep: true,
    },
  },

  mounted() {
    // 部署限制
    this.fetchEnvProtection();

    // 出口IP管理
    this.getGatewayInfos('stag');
    this.getGatewayInfos('prod');
  },
  methods: {
    handleProcessNameEdit() {},

    async fetchEnvProtection() {
      try {
        const res = await this.$store.dispatch('module/getEnvProtection', {
          appCode: this.appCode,
          modelName: this.curModuleId,
        });
        console.log('res', res);
        if (res.length) {
          if (res.length === 2) {
            res.forEach((item) => {
              this.deployLimit[item.environment] = true;
            });
          } else {
            const curEnv = res[0].environment;
            if (curEnv === 'stag') {
              this.deployLimit.stag = true;
              this.deployLimit.prod = false;
            } else {
              this.deployLimit.stag = false;
              this.deployLimit.prod = true;
            }
          }
        } else {
          this.deployLimit = {
            stag: false,
            prod: false,
          };
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },

    // 设置部署限制环境
    async fetchSetDeployLimit(env) {
      try {
        await this.$store.dispatch('module/setDeployLimit', {
          appCode: this.appCode,
          modelName: this.curModuleId,
          params: {
            operation: 'deploy',
            env,
          },
        });
      } catch (res) {
        this.deployLimit[env] = !this.deployLimit[env];
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },


    getGatewayInfos(env) {
      const appCode = this.$route.params.id;
      this.$store.dispatch('baseInfo/getGatewayInfos', {
        appCode,
        env,
        moduleName: this.curAppModule.name,
      }).then((res) => {
        this.gatewayInfos[env] = {
          created: moment(res.rcs_binding_data.created).startOf('minute')
            .fromNow(),
          node_ip_addresses: res.rcs_binding_data.state.node_ip_addresses,
        };
        this.gatewayEnabled[env] = true;
      })
        .catch(() => {
          this.gatewayInfos[env] = {
            created: '',
            node_ip_addresses: [],
          };
          this.gatewayEnabled[env] = false;
        });
    },
  },
};
</script>
<style lang="scss" scoped>
  .module-info-container{
    padding: 0 20px 20px;
    .base-info-title{
      color: #313238;
      font-size: 14px;
      font-weight: bold;
    }
    .edit-container{
      color: #3A84FF;
      font-size: 12px;
      cursor: pointer;
    }

    .form-detail{
      .form-text{
          color: #313238;
        }
    }

    .border-b{
      border-bottom: 1px solid #dcdee5;
    }

    .ip-info-container{
        .content {
            margin-top: 20px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
            &.no-border {
                border: none;
            }
            .info-special-form:nth-child(2) {
                position: relative;
                top: -4px;
            }
            .title-label {
                display: inline-block;
                padding-left: 20px;
                width: 140px;
                height: 42px;
                line-height: 42px;
                border: 1px solid #dcdee5;
                color: #313238;
                &.pl {
                    padding-left: 62px;
                }
            }
            .module-name,
            .module-init-type {
                display: inline-block;
                position: relative;
                padding-left: 16px;
                width: 821px;
                line-height: 40px;
                border-top: 1px solid #dcdee5;
                border-right: 1px solid #dcdee5;
                border-bottom: 1px solid #dcdee5;
            }
            .switcher-content {
                position: absolute;
                display: inline-block;
                margin-left: 20px;
                font-size: 12px;
                color: #979ba5;
                line-height: 24px;
            }
            .switch-button {
                margin-top: 20px;
                padding-left: 100px;
            }
            .pre-release-wrapper,
            .production-wrapper {
                display: inline-block;
                position: relative;
                width: 48%;
                border: 1px solid #dcdee5;
                border-radius: 2px;
                vertical-align: top;
                float: left;
                &.has-left {
                    float: right;
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
                    padding: 14px 40px 14px 14px;
                    height: 138px;
                    overflow-x: hidden;
                    overflow-y: auto;
                    .copy-wrapper {
                        position: absolute;
                        right: 20px;
                        top: 48px;
                        font-size: 16px;
                        cursor: pointer;
                        &:hover {
                            color: #3a84ff;
                        }
                    }
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
                padding-top: 7px;
                color: #63656e;
                font-size: 12px;
                clear: both;
                i {
                    color: #ff9c01;
                }
            }
        }
    }

    .info {
        color: #979ba5;
        font-size: 12px;
    }
  }
</style>
