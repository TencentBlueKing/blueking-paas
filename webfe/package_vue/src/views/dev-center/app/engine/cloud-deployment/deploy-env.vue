<template lang="html">
  <div class="env-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-env-loading"
      class="app-container middle"
    >
      <section v-show="!isLoading">
        <p class="desc-env">
          {{ $t('环境变量可以用来改变应用在不同环境下的行为；除自定义环境变量外，平台也会写入内置环境变量。') }}
          <span
            class="built-in-env"
            @click="handleShoEnvDialog"
          >{{ $t('查看内置环境变量') }}</span>
        </p>
        <div class="filter-list">
          <div class="label">
            <i class="paasng-icon paasng-funnel" />
            {{ $t('生效环境：') }}
          </div>
          <div class="bk-button-group">
            <bk-button
              theme="primary"
              style="width: 130px;"
              :outline="curStage !== '_global_'"
              @click="changeConfigVarByEnv('_global_')"
            >
              {{ $t('所有环境') }}
            </bk-button>
            <bk-button
              theme="primary"
              style="width: 130px;"
              :outline="curStage !== 'stag'"
              @click="changeConfigVarByEnv('stag')"
            >
              {{ $t('仅预发布环境') }}
            </bk-button>
            <bk-button
              theme="primary"
              style="width: 130px;"
              :outline="curStage !== 'prod'"
              @click="changeConfigVarByEnv('prod')"
            >
              {{ $t('仅生产环境') }}
            </bk-button>
          </div>
          <!-- 默认不展示 -->
          <bk-button
            v-if="curStage !== ''"
            ext-cls="reset-button"
            theme="primary"
            text
            @click="handleReset"
          >
            {{ $t('重置') }}
          </bk-button>
          <!-- <bk-button ext-cls="env-sort-btn" slot="dropdown-trigger" @click="handleSort">
                        <i class="paasng-icon paasng-general-sort sort-icon"></i>
                        <span class="text"> {{ $t('排序') }} </span>
                    </bk-button> -->
          <!-- <bk-dropdown-menu
                        ext-cls="env-sort-btn"
                        trigger="click"
                        align="right"
                        @show="dropdownShow"
                        @hide="dropdownHide"
                        ref="dropdown">
                        <bk-button
                            slot="dropdown-trigger">
                            <i class="paasng-icon paasng-general-sort sort-icon"></i>
                            <span class="text"> {{ $t('排序') }} </span>
                        </bk-button>
                        <ul class="bk-dropdown-list" slot="dropdown-content">
                            <li><a href="javascript:;" style="margin: 0;" :class="curSortKey === 'key' ? 'active' : ''" @click="handleSort">{{ $t('KEY 名称(A-Z)') }}</a></li>
                        </ul>
                    </bk-dropdown-menu> -->
        </div>
        <table
          v-if="envVarList.length"
          v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
          class="ps-table ps-table-default ps-table-width-overflowed"
          style="margin-bottom: 24px;"
        >
          <tr
            v-for="(varItem, index) in envVarList"
            :key="index"
          >
            <td>
              <bk-form
                ref="envRef"
                form-type="inline"
                :model="varItem"
              >
                <bk-form-item
                  :rules="varRules.name"
                  :property="'name'"
                  style="flex: 1 1 25%;"
                >
                  <bk-input
                    v-model="varItem.name"
                    placeholder="NAME"
                    :clearable="false"
                    :readonly="isReadOnlyRow(index)"
                    @enter="handleEnter(index)"
                  />
                </bk-form-item>
                <bk-form-item
                  :rules="varRules.value"
                  :property="'value'"
                  style="flex: 1 1 25%;"
                >
                  <template v-if="isReadOnlyRow(index)">
                    <div
                      v-bk-tooltips="{ content: varItem.value, trigger: 'mouseenter', maxWidth: 400, extCls: 'env-var-popover' }"
                      class="desc-form-content"
                    >
                      {{ varItem.value }}
                    </div>
                  </template>
                  <template v-else>
                    <bk-input
                      v-model="varItem.value"
                      placeholder="VALUE"
                      :clearable="false"
                      :readonly="isReadOnlyRow(index)"
                      @enter="handleEnter(index)"
                    />
                  </template>
                </bk-form-item>
                <bk-form-item style="flex: 1 1 18%;">
                  <bk-select
                    v-model="varItem.envName"
                    :disabled="isReadOnlyRow(index)"
                    :placeholder="$t('请选择')"
                    :clearable="false"
                  >
                    <bk-option
                      v-for="(option, optionIndex) in envSelectList"
                      :id="option.id"
                      :key="optionIndex"
                      :name="option.text"
                    />
                  </bk-select>
                </bk-form-item>
                <bk-form-item style="text-align: right; min-width: 80px;">
                  <template v-if="isReadOnlyRow(index)">
                    <a
                      class="paasng-icon paasng-edit ps-btn ps-btn-icon-only btn-ms-primary"
                      @click="editingRowToggle(varItem, index)"
                    />
                    <tooltip-confirm
                      ref="deleteTooltip"
                      :ok-text="$t('确定')"
                      :cancel-text="'取消'"
                      :theme="'ps-tooltip'"
                      @ok="deleteEnvData(index, varItem)"
                    >
                      <a
                        v-show="isReadOnlyRow(index)"
                        slot="trigger"
                        class="paasng-icon paasng-delete ps-btn ps-btn-icon-only btn-ms-primary"
                      />
                    </tooltip-confirm>
                  </template>
                  <template v-else>
                    <a
                      class="paasng-icon paasng-check-1 ps-btn ps-btn-icon-only"
                      type="submit"
                      @click="updateEnvData(index, varItem)"
                    />
                    <a
                      class="paasng-icon paasng-close ps-btn ps-btn-icon-only"
                      style="margin-left: 0;"
                      @click="editingRowToggle(varItem, index, 'cancel')"
                    />
                  </template>
                </bk-form-item>
              </bk-form>
            </td>
          </tr>
        </table>
        <div
          v-else
          class="ps-no-result"
        >
          <div class="text">
            <img
              class="img-exception"
              src="/static/images/empty.png"
              alt=""
            >
            <p class="text-exception">
              {{ $t('暂无数据') }}
            </p>
          </div>
        </div>
        <bk-button
          theme="primary"
          :outline="true"
          @click.stop.prevent="addEnvData"
        >
          {{ $t('添加') }}
        </bk-button>
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

<script>
    import _ from 'lodash';
    // import dropdown from '@/components/ui/Dropdown';
    import tooltipConfirm from '@/components/ui/TooltipConfirm';
    import appBaseMixin from '@/mixins/app-base-mixin';

    export default {
        components: {
            // dropdown,
            tooltipConfirm
        },
        mixins: [appBaseMixin],
        props: {
            cloudAppData: {
                type: Object,
                default: {}
            }
        },
        data () {
            return {
                envVarList: [],
                envVarListBackup: [],
                runtimeImageList: [],
                buildpackValueList: [],
                runtimeImage: '',
                runtimeBuild: [],
                isRuntimeUpdaing: false,
                availableEnv: [],
                isEdited: false,
                isReleased: false,
                deleteToolTipShow: false,
                newVarConfig: {
                    key: '',
                    value: '',
                    env: 'stag',
                    description: ''
                },
                varRules: {
                    name: [
                        {
                            required: true,
                            message: this.$t('NAME是必填项'),
                            trigger: 'blur'
                        },
                        {
                            regex: /^[-._a-zA-Z][-._a-zA-Z0-9]*$/,
                            message: this.$t('环境变量名称必须由字母字符、数字、下划线（_）、连接符（-）、点（.）组成，并且不得以数字开头（例如“my.env-name”或“MY_ENV.NAME”, 或 “MyEnvName1”）'),
                            trigger: 'blur'
                        }
                    ],
                    value: [
                        {
                            required: true,
                            message: this.$t('VALUE是必填项'),
                            trigger: 'blur'
                        },
                        {
                            max: 2048,
                            message: this.$t('不能超过2048个字符'),
                            trigger: 'blur'
                        }
                    ],
                    description: [
                        {
                            validator: value => {
                                if (value === '') {
                                    return true;
                                }
                                return value.trim().length <= 200;
                            },
                            message: this.$t('不能超过200个字符'),
                            trigger: 'blur'
                        }
                    ]
                },
                addingConfigVarEnv: 'stag',
                editRowList: [],
                isLoading: true,
                isVarLoading: true,
                activeEnvTab: '',
                updateFormList: [],
                runtimeDialogConf: {
                    visiable: false,
                    image: '',
                    buildpacks: [],
                    buildpackValueList: []
                },

                isDropdownShow: false,
                curSortKey: '-created',

                exportDialog: {
                    visiable: false,
                    width: 480,
                    headerPosition: 'center',
                    loading: false,
                    isLoading: false,
                    count: 0
                },
                exportFileDialog: {
                    visiable: false,
                    width: 540,
                    headerPosition: 'center',
                    loading: false
                },
                moduleValue: '',
                curSelectModuleName: '',
                curFile: {},
                isFileTypeError: false,
                envItemBackUp: {},
                envSidesliderConf: {
                    visiable: false
                },
                basicInfo: [],
                appRuntimeInfo: [],
                bkPlatformInfo: [],
                loadingConf: {
                    basicLoading: false,
                    appRuntimeLoading: false,
                    bkPlatformLoading: false
                },
                globalSelectList: [

                ],
                envSelectList: [
                    { id: '_global_', text: this.$t('所有环境') },
                    { id: 'stag', text: this.$t('预发布环境') },
                    { id: 'prod', text: this.$t('生产环境') }
                ],
                curStage: '',
                allReplicaList: [],
                envReplicaList: [],
                isTableLoading: true,
                allEnvVarList: []
            };
        },
        computed: {
            runtimeBuildpacks () {
                let result = [];
                const image = this.runtimeImageList.find(item => {
                    return item.image === this.runtimeDialogConf.image;
                });
                const buildpacks = image ? [...image.buildpacks] : [];

                // 兼容穿梭框右侧排序问题，后续调整组件
                this.runtimeBuild.forEach(id => {
                    buildpacks.forEach((item, index) => {
                        if (item.id === id) {
                            result.push(item);
                            buildpacks.splice(index, 1);
                        }
                    });
                });
                result = result.concat(buildpacks);

                return result;
            },
            runtimeBuildpacksId () {
                return this.runtimeBuildpacks.map(item => {
                    return item.id;
                });
            },
            runtimeImageText () {
                const result = this.runtimeImageList.find(item => {
                    return item.image === this.runtimeImage;
                });
                if (result) {
                    return result.name || result.image;
                } else {
                    return '';
                }
            },
            runtimeBuildTexts () {
                const builds = [];
                const image = this.runtimeImageList.find(item => {
                    return item.image === this.runtimeImage;
                });
                const buildpacks = image ? image.buildpacks : [];
                this.runtimeBuild.forEach(item => {
                    buildpacks.forEach(pack => {
                        if (pack.id === item) {
                            builds.push(pack);
                        }
                    });
                });
                return builds;
            },
            globalEnvName () {
                if (_.includes(this.availableEnv, 'stag') && _.includes(this.availableEnv, 'prod')) {
                    return '_global_';
                } else {
                    return this.availableEnv[0];
                }
            },
            curModuleList () {
                return this.curAppModuleList.filter(item => item.name !== this.curModuleId);
            },
            envLoading () {
                return this.loadingConf.basicLoading || this.loadingConf.appRuntimeLoading || this.loadingConf.bkPlatformLoading;
            }
        },
        watch: {
            '$route' () {
                // this.init();
            },
            cloudAppData: {
                handler (val) {
                    if (val.spec) {
                        this.localCloudAppData = _.cloneDeep(val);
                        // 所有环境
                        this.allEnvVarList = [...val.spec.configuration.env];
                        if (val.spec.envOverlay && val.spec.envOverlay.envVariables) {
                            this.allEnvVarList.push(...val.spec.envOverlay.envVariables);
                        }
                        this.allEnvVarList.forEach(item => {
                            if (!item.envName) {
                                this.$set(item, 'envName', '_global_');
                            }
                        });
                        this.envVarList = val.spec.configuration.env;

                        if (this.curStage === '') {
                            const all = [...this.envVarList];
                            if (val.spec.envOverlay && val.spec.envOverlay.envVariables) {
                                all.push(...val.spec.envOverlay.envVariables);
                            }
                            this.envVarList = all;
                        }

                        setTimeout(() => {
                            this.isLoading = false;
                            this.isTableLoading = false;
                        }, 500);
                    }
                },
                immediate: true
                // deep: true
            },
            // allReplicaList: {
            //     handler (val) {
            //         this.envReplicaList = val.filter(item => item.envName === this.curStage);
            //     }
            // },
            curStage (value) {
                this.isTableLoading = true;
                if (!value) {
                    this.envVarList = this.allEnvVarList;
                } else {
                    this.envVarList = this.allEnvVarList.filter(item => item.envName === value);
                }
                setTimeout(() => {
                    this.isTableLoading = false;
                }, 200);
            }
        },
        created () {
            // this.init();
        },
        methods: {

            dropdownShow () {
                this.isDropdownShow = true;
            },
            dropdownHide () {
                this.isDropdownShow = false;
            },
            handleReset () {
                this.curStage = '';
            },
            init () {
                this.isLoading = true;
                this.isEdited = false;
                this.curSortKey = '-created';
                // this.loadConfigVar();
                this.fetchReleaseInfo();
                this.getAllImages();
            },
            fetchReleaseInfo () {
                // 这里分别调用预发布环境 和 生产环境的 API，只要有一个返回 200，isReleased 就要设置为 True
                this.$http.get(BACKEND_URL + '/api/bkapps/applications/' + this.appCode + '/modules/' + this.curModuleId + '/envs/stag' + '/released_state/?with_processes=true').then((response) => {
                    this.isReleased = true;
                    this.availableEnv.push('stag');
                }, (errRes) => {
                    console.error(errRes);
                });

                this.$http.get(BACKEND_URL + '/api/bkapps/applications/' + this.appCode + '/modules/' + this.curModuleId + '/envs/prod' + '/released_state/?with_processes=true').then((response) => {
                    this.isReleased = true;
                    this.availableEnv.push('prod');
                }, (errRes) => {
                    console.error(errRes);
                });
            },
            async getAllImages () {
                try {
                    const res = await this.$store.dispatch('envVar/getAllImages', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId
                    });

                    if (res.results) {
                        res.results.forEach(item => {
                            item.name = `${item.slugbuilder.display_name || item.image} (${item.slugbuilder.description || '--'})`;

                            item.buildpacks.forEach(item => {
                                item.name = `${item.display_name || item.name} (${item.description || '--'})`;
                            });
                        });
                        this.runtimeImageList = res.results;
                    }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                }
            },
            isReadOnlyRow (rowIndex) {
                return !_.includes(this.editRowList, rowIndex);
            },
            isEnvAvailable (envName) {
                return _.includes(this.availableEnv, envName);
            },
            editingRowToggle (rowItem, rowIndex, type = '') {
                if (rowItem.isAdd) {
                    // 直接删除
                    this.envVarList.splice(rowIndex, 1);
                } else {
                    if (type === 'cancel') {
                        if (Object.keys(this.envItemBackUp).length === 0) { // 如果没有任何内容 则删除
                            this.envVarList.splice(rowIndex, 1);
                        } else {
                            this.envVarList.splice(rowIndex, 1, this.envItemBackUp);
                        }
                        this.editRowList = this.editRowList.filter(e => e !== rowIndex);
                    } else {
                        this.envItemBackUp = _.cloneDeep(rowItem);
                        if (_.includes(this.editRowList, rowIndex)) {
                            this.editRowList = this.editRowList.filter(e => e !== rowIndex);
                        } else {
                            this.editRowList.push(rowIndex);
                        }
                    }
                }
            },
            // 修改完成
            async updateEnvData (rowIndex, rowItem) {
                // 是否已存在
                if (rowItem.isAdd) {
                    const isExist = this.isExistsVarName(rowItem);
                    if (!isExist) {
                        return;
                    }
                }
                this.$refs.envRef[rowIndex].validate().then(() => {
                    this.isTableLoading = true;
                    if (!this.localCloudAppData.spec.envOverlay) {
                        this.$set(this.localCloudAppData.spec, 'envOverlay', {});
                    }
                    if (this.curStage !== '' && rowItem.isAdd) {
                        this.allEnvVarList.push(rowItem);
                    }
                    // 该环境是否已存在
                    if (this.curStage === '') {
                        const allEnvList = this.envVarList.filter(item => item.envName === '_global_');
                        const otherEnvList = this.envVarList.filter(item => item.envName !== '_global_');
                        this.$set(this.localCloudAppData.spec.configuration, 'env', allEnvList);
                        this.$set(this.localCloudAppData.spec.envOverlay, 'envVariables', otherEnvList);
                    } else {
                        if (this.curStage === '_global_') {
                            if (rowItem.envName === '_global_') {
                                this.$set(this.localCloudAppData.spec.configuration, 'env', this.envVarList);
                            } else {
                                this.setLocalCloudAppData();
                            }
                        } else {
                            if (rowItem.envName === '_global_') {
                                this.setLocalCloudAppData();
                            } else {
                                this.setLocalCloudAppData();
                            }
                        }
                    }
                    this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                    if (_.includes(this.editRowList, rowIndex)) {
                        this.editRowList = this.editRowList.filter(e => e !== rowIndex);
                    }
                    this.$nextTick(() => {
                        // 更新数据源
                        const spec = this.localCloudAppData.spec;
                        this.allEnvVarList = [...spec.configuration.env];
                        if (spec.envOverlay && spec.envOverlay.envVariables) {
                            this.allEnvVarList.push(...spec.envOverlay.envVariables);
                        }

                        this.allEnvVarList.forEach(item => {
                            if (!item.envName) {
                                this.$set(item, 'envName', '_global_');
                            }
                            if (item.isAdd) {
                                delete item.isAdd;
                            }
                        });
                        setTimeout(() => {
                            this.redisplay();
                            this.isTableLoading = false;
                        }, 200);
                    });
                });
            },
            // 处理回车
            handleEnter (i) {
                this.updateEnvData(i);
            },
            addEnvData () {
                const isAdd = this.envVarList.find(item => item.isAdd);
                if (isAdd) {
                    return;
                }
                this.envVarList.push({
                    name: '',
                    value: '',
                    envName: this.curStage || '_global_',
                    isAdd: true
                });
                this.editRowList.push(this.envVarList.length - 1);
            },
            // 保留当前的新建
            deleteEnvData (rowIndex, rowItem) {
                this.isTableLoading = true;
                // this.envVarList.splice(rowIndex, 1);
                if (!this.localCloudAppData.spec.envOverlay) {
                    this.$set(this.localCloudAppData.spec, 'envOverlay', {});
                }
                const editEnvList = this.envVarList.filter((item, index) => !this.isReadOnlyRow(index) || item.isAdd);
                this.allEnvVarList = this.allEnvVarList.filter((item, index) => {
                    const isEdit = this.isReadOnlyRow(index);
                    if (!item.isAdd && isEdit) {
                        return true;
                    }
                });
                if (this.curStage === '') {
                    if (rowItem.envName === '_global_') {
                        const results = this.allEnvVarList.filter(item => item.envName === '_global_' && item.name !== rowItem.name);
                        this.$set(this.localCloudAppData.spec.configuration, 'env', results);
                    } else {
                        // 区分环境删除
                        const results = this.allEnvVarList.filter(item => item.envName !== '_global_');
                        results.forEach(item => {
                            if (item.envName === rowItem.envName && item.name === rowItem.name) {
                                item.isDelete = true;
                            }
                        });
                        const filterEnvList = results.filter(item => !item.isDelete);
                        this.$set(this.localCloudAppData.spec.envOverlay, 'envVariables', filterEnvList);
                    }
                } else {
                    if (rowItem.envName === '_global_') {
                        const results = this.allEnvVarList.filter(item => item.envName === '_global_' && item.name !== rowItem.name);
                        this.$set(this.localCloudAppData.spec.configuration, 'env', results);
                    } else {
                        const results = this.allEnvVarList.filter(item => item.envName !== '_global_');
                        results.forEach(item => {
                            if (item.envName === rowItem.envName && item.name === rowItem.name) {
                                item.isDelete = true;
                            }
                        });
                        const filterEnvList = results.filter(item => !item.isDelete);
                        this.$set(this.localCloudAppData.spec.envOverlay, 'envVariables', filterEnvList);
                    }
                }
                this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
                if (this.$refs.deleteTooltip[rowIndex]) {
                    this.$refs.deleteTooltip[rowIndex].cancel();
                }
                this.$nextTick(() => {
                    // 更新
                    const spec = this.localCloudAppData.spec;
                    this.allEnvVarList = [...spec.configuration.env];
                    if (spec.envOverlay && spec.envOverlay.envVariables) {
                        this.allEnvVarList.push(...spec.envOverlay.envVariables);
                    }
                    this.allEnvVarList.forEach(item => {
                        if (!item.envName) {
                            this.$set(item, 'envName', '_global_');
                        }
                        if (item.isAdd) {
                            delete item.isAdd;
                        }
                    });
                    // 并把当前项改为编辑状态
                    this.allEnvVarList.push(...editEnvList);
                    // 重新获取环境列表
                    this.envVarList = this.allEnvVarList;
                    if (this.curStage) {
                        this.envVarList = this.allEnvVarList.filter(item => item.envName === this.curStage);
                    }
                    this.envVarList.forEach((item, index) => {
                        if (item.isAdd) {
                            this.editRowList.push(index);
                        }
                    });
                    setTimeout(() => {
                        this.isTableLoading = false;
                    }, 200);
                });
            },
            cancelDelete () {
                this.$refs.deleteTooltip[0].close();
            },
            releaseEnv (envName) {
                this.$refs.releaseDropDown.close();
                this.$http.post(BACKEND_URL + '/api/bkapps/applications/' + this.appCode + '/modules/' + this.curModuleId + '/envs/' + envName + '/releases/').then((response) => {
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('发布提交成功，请在进程管理查看发布情况')
                    });
                }, (errRes) => {
                    const errorMsg = errRes.message;
                    this.$paasMessage({
                        theme: 'error',
                        message: errorMsg
                    });
                });
                this.isEdited = false;
            },
            skipRelease () {
                this.isEdited = false;
            },
            handleHideRuntimeDialog () {},

            handleBuildpackChange (sourceList, targetList, targetValueList) {
                this.runtimeDialogConf.buildpacks = targetValueList;
            },

            handleImageChange () {
                this.runtimeDialogConf.buildpacks = [];
                this.runtimeDialogConf.buildpackValueList = [];
            },

            formDataValidate (index) {
                this.$refs.envRef[index].validate();
            },

            handleShoEnvDialog () {
                this.envSidesliderConf.visiable = true;
            },

            showEnvVariable () {
                this.getBasicInfo();
                this.getAppRuntimeInfo();
                this.getBkPlatformInfo();
            },

            async getBasicInfo () {
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
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.loadingConf.basicLoading = false;
                }
            },

            async getAppRuntimeInfo () {
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
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.loadingConf.appRuntimeLoading = false;
                }
            },

            async getBkPlatformInfo () {
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
                        message: e.message || e.detail || this.$t('接口异常')
                    });
                } finally {
                    setTimeout(() => {
                        this.loadingConf.bkPlatformLoading = false;
                    }, 300);
                }
            },

            convertArray (data) {
                const list = [];
                for (const key in data) {
                    list.push({
                        label: key,
                        value: data[key],
                        isTips: true
                    });
                }
                return list;
            },

            // 文字溢出显示tooltips
            contrastTextWitch (parentRef, childRef, data) {
                const containerWitch = this.$refs[parentRef].offsetWidth;
                this.$refs[childRef].forEach((item, index) => {
                    if (item.offsetWidth > containerWitch) {
                        this.$set(data[index], 'isTips', false);
                    }
                });
            },

            // 切换对应环境
            changeConfigVarByEnv (env) {
                this.curStage = env;
            },

            isExistsVarName (curItem) {
                const spec = this.localCloudAppData.spec;
                const sourceList = [...spec.configuration.env];
                if (spec.envOverlay && spec.envOverlay.envVariables) {
                    sourceList.push(...spec.envOverlay.envVariables);
                }
                const flag = sourceList.find(item => item.name === curItem.name && item.envName === curItem.envName);
                if (flag) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `该环境下名称为 ${curItem.name} 的变量已经存在，不能重复添加。`
                    });
                    return false;
                }
                return 'single';
            },

            handleSort () {
                this.isTableLoading = true;
                if (this.curStage === '_global_') {
                    if (this.envVarList.length > 1) {
                        this.alphabeticalOrder(this.envVarList);
                    }
                } else {
                    if (this.allReplicaList.length > 1) {
                        this.alphabeticalOrder(this.allReplicaList);
                    }
                }
                setTimeout(() => {
                    this.isTableLoading = false;
                }, 200);
            },

            // 首字母排序
            alphabeticalOrder (targetArr) {
                targetArr.sort((a, b) => {
                    const textA = a.name.toUpperCase();
                    const textB = b.name.toUpperCase();
                    return (textA < textB) ? -1 : (textA > textB) ? 1 : 0;
                });
            },

            redisplay () {
                if (!this.curStage) {
                    this.envVarList = this.allEnvVarList;
                } else {
                    this.envVarList = this.allEnvVarList.filter(item => item.envName === this.curStage);
                }
            },

            setLocalCloudAppData () {
                const allEnvList = this.envVarList.filter(item => item.envName === '_global_');
                const otherEnvList = this.allEnvVarList.filter(item => item.envName !== '_global_');
                this.$set(this.localCloudAppData.spec.configuration, 'env', allEnvList);
                this.$set(this.localCloudAppData.spec.envOverlay, 'envVariables', otherEnvList);
            }
        }
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
        padding: 20px;
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
</style>
