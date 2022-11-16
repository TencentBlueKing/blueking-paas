<template>
  <div class="port-config">
    <div class="ps-top-card">
      <p class="main-title">
        {{ $t('访问地址') }}
      </p>
      <p class="desc">
        <span v-if="curAppInfo.application.region === 'ieod'"> {{ $t('平台给应用分配了默认的 oa 域和 woa 域的地址，若需要使用HTTPS请参考') }} </span>
        <span v-else> {{ $t('平台给应用分配的默认访问地址') }} </span>
        <a
          :href="GLOBAL.DOC.APP_ENTRY_INTRO"
          target="blank"
        > {{ $t('详细使用说明') }} </a>
      </p>
    </div>
    <div
      class="content"
      style="position: relative;"
    >
      <table
        class="ps-table ps-table-border mt20"
        style="width: 100%;"
      >
        <!-- 通过 type 判断是子域名还是子路径（1. 子路径 2. 子域名） -->
        <!-- 通过 is_running 判断域名是否可以访问，可访问前端样式为 href，不可访问时为普通文本 -->
        <tr>
          <td class="has-right-border td-title">
            {{ $t('当前类型') }}
          </td>
          <td>{{ moduleEntryInfo.type === 1 ? $t('子路径') : $t('子域名') }}</td>
        </tr>
        <tr v-if="rootDomains.length > 1">
          <td class="has-right-border td-title">
            {{ $t('默认根域') }}
          </td>
          <td
            class="root-domains-row"
            :class="{ 'td-focus': isEdited }"
            style=""
          >
            <div class="root-domains-wrapper">
              <div
                v-for="(item,index) in rootDomains"
                :key="index"
                class="pt10 pb10 root-domain"
              >
                <bk-radio-group v-model="rootDomainDefault">
                  <bk-radio
                    :value="item"
                    :disabled="!isEdited"
                  >
                    <span class="root-url">{{ item || '--' }}</span>
                  </bk-radio>
                </bk-radio-group>
              </div>
            </div>
            <div class="action-box">
              <template v-if="!isEdited">
                <a
                  v-bk-tooltips="$t('编辑')"
                  class="paasng-icon paasng-edit2"
                  @click="showEdit"
                />
              </template>
              <template v-else>
                <bk-button
                  style="margin-right: 6px;"
                  theme="primary"
                  text
                  :disabled="rootDomainDefaultDiff === rootDomainDefault"
                  @click.stop.prevent="handleShowDialog"
                >
                  {{ $t('保存') }}
                </bk-button>
                <bk-button
                  theme="primary"
                  text
                  @click.stop.prevent="handleCancel"
                >
                  {{ $t('取消') }}
                </bk-button>
              </template>
            </div>
          </td>
        </tr>
        <tr
          v-for="(item, key) of moduleEntryInfo.entrancesTemplate"
          :key="key"
        >
          <td class="has-right-border td-title">
            {{ key === 'prod' ? $t('生产') : $t('预发布') }}{{ $t('环境') }}
          </td>
          <td>
            <div
              v-for="e in item"
              :key="e.address"
              class="pt10 pb10"
            >
              <span>{{ e.address || '--' }}</span>
              <a
                v-if="e.is_running"
                :href="e.address"
                target="_blank"
                class="card-edit ml5 f12"
              >
                {{ $t('点击访问') }}
              </a>
            </div>
          </td>
        </tr>
      </table>
      <bk-button
        v-if="moduleEntryInfo.type === 1 && canUpdateSubDomain"
        class="toggle-type"
        :text="true"
        theme="primary"
        @click="visitDialog.visiable = true"
      >
        {{ $t('切换为子域名') }}
      </bk-button>

      <bk-dialog
        v-model="visitDialog.visiable"
        width="600"
        :title="visitDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        :loading="isLoading"
        @confirm="handleConfirm"
        @cancel="visitDialog.visiable = false"
      >
        <div class="tl">
          <p> {{ $t('注意事项：') }} </p>
          <p> {{ $t('1、应用的主访问路径将会变为子域名方式') }} </p>
          <p> {{ $t('2、如果应用框架代码没有适配过独立域名访问方式，一些静态文件路径可能会出现问题') }} </p>
          <p> {{ $t('3、旧的子路径地址依然有效，可以正常访问') }} </p>
        </div>
      </bk-dialog>

      <bk-dialog
        width="600"
        :value="domainDialog.visiable"
        :title="domainDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        @confirm="updateRootDomain"
        @cancel="domainDialog.visiable = false"
      >
        <div class="tl">
          <p> {{ $t('更改后：') }} </p>
          <p>1. {{ $t('该模块的默认访问地址的根域为变为：') }}{{ rootDomainDefault }}</p>
          <p>2. {{ $t('若该模块为主模块，则应用市场访问地址的根域也会变为：') }}{{ rootDomainDefault }}</p>
        </div>
      </bk-dialog>
    </div>
  </div>
</template>

<script type="text/javascript">
    import appBaseMixin from '@/mixins/app-base-mixin';

    export default {
        mixins: [appBaseMixin],
        data () {
            return {
                type: '',
                example: '',
                canUpdateSubDomain: false,
                isLoading: false,
                visitDialog: {
                    visiable: false,
                    title: this.$t('确认切换为子域名访问地址？')
                },
                moduleEntryInfo: {
                    entrances: [],
                    type: 1,
                    entrancesTemplate: {}
                },
                region: '',
                rootDomains: [],
                rootDomainDefault: '',
                isEdited: false,
                domainDialog: {
                    visiable: false,
                    title: this.$t('确认更改默认根域？')
                },
                rootDomainDefaultDiff: ''
            };
        },
        computed: {
            platformFeature () {
                return this.$store.state.platformFeature;
            }
        },
        watch: {
            '$route' () {
                this.init();
            }
        },
        created () {
            this.init();
        },
        methods: {
            /**
             * 数据初始化入口
             */
            init () {
                this.getAppRegion();
                this.getEntryInfo();
                this.getDefaultDomainInfo();
            },

            async getAppRegion () {
                this.canUpdateSubDomain = false;
                try {
                    const region = this.curAppInfo.application.region;
                    const res = await this.$store.dispatch('getAppRegion', region);
                    this.canUpdateSubDomain = res.entrance_config.manually_upgrade_to_subdomain_allowed;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.$emit('data-ready', 'visit-config');
                }
            },

            async getEntryInfo () {
                try {
                    const res = await this.$store.dispatch('entryConfig/getEntryInfo', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });
                    this.moduleEntryInfo = res;
                    this.moduleEntryInfo.entrancesTemplate = res.entrances.reduce((p, v) => {
                        p[v.env].push(v);
                        return p;
                    }, { 'stag': [], 'prod': [] });
                } catch (e) {
                    this.moduleEntryInfo = {
                        entrances: [],
                        type: 1,
                        entrancesTemplate: {}
                    };
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            async handleConfirm () {
                this.isLoading = true;
                try {
                    await this.$store.dispatch('entryConfig/updateEntryType', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        type: 2
                    });
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('修改成功')
                    });
                    this.$store.commit('updateCurAppModuleExposed', 2);
                    this.visitDialog.visiable = false;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.isLoading = false;
                }
            },

            async getDefaultDomainInfo () {
                try {
                    const res = await this.$store.dispatch('entryConfig/getDefaultDomainInfo', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });
                    this.rootDomains = res.root_domains || [];
                    this.rootDomainDefault = res.preferred_root_domain;
                    this.rootDomainDefaultDiff = res.preferred_root_domain;
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },

            async updateRootDomain () {
                try {
                    await this.$store.dispatch('entryConfig/updateRootDomain', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        data: {
                            preferred_root_domain: this.rootDomainDefault
                        }
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('修改成功')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.isEdited = false;
                    this.domainDialog.visiable = false;
                    this.getDefaultDomainInfo();
                }
            },

            showEdit () {
                this.isEdited = true;
            },

            handleShowDialog () {
                if (this.rootDomainDefaultDiff !== this.rootDomainDefault) {
                    this.domainDialog.visiable = true;
                }
            },

            handleCancel () {
                this.isEdited = false;
                if (this.rootDomainDefaultDiff !== this.rootDomainDefault) {
                    this.getDefaultDomainInfo();
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .toggle-type {
        position: absolute;
        right: 20px;
        top: 11px;
    }

    .root-domains-row {
        display: flex;
        justify-content: space-between;
    }

    .root-domains-wrapper {
        display: flex;
        .root-domain:nth-child(n + 2) {
            margin-left: 20px;
        }
    }

    .action-box {
        line-height: 40px;
        margin-right: 20px;
    }

    .root-url {
        font-size: 13px;
    }

    .td-focus {
        border: 1px solid #3a84ff;
        transition: all .1s;
        transform: translateY(-1px);
    }
    .td-title {
        width: 180px;
        text-align: center;
        padding: 0;
    }
</style>
