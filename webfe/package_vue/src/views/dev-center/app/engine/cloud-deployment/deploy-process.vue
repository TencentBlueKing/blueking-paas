<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-process-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="process-container">
      <!-- <div class="tab-container">
        <div class="tab-list">
          <div
            v-for="(panel, index) in panels"
            :key="index"
            class="tab-item"
            :class="[{ 'isActive': panelActive === index }]"
            @click="handlePanelClick(index, $event, 'add')"
            @mouseenter="handlePanelEnter(index)"
            @mouseleave="handlePanelLeave"
          >
            <div v-if="panel.isEdit">
              <bk-input
                ref="panelInput"
                v-model="itemValue"
                style="width: 100px"
                :placeholder="$t('进程名称')"
                ext-cls="bk-input-cls"
                @enter="handleEnter"
                @blur="handleBlur"
              />
            </div>
            <span
              v-else
              class="panel-name"
            >{{ panel.name }}</span>
            <i
              v-if="showEditIconIndex === index && !panel.isEdit"
              class="paasng-icon paasng-icon-close item-close-icon"
              @click.stop="handleDelete(index)"
            />
            <i
              v-if="showEditIconIndex === index && !panel.isEdit && panelActive !== index"
              class="paasng-icon paasng-edit2 edit-name-icon"
              @click.stop="handleIconClick(index)"
            />
          </div>
          <i
            class="paasng-icon paasng-plus-thick add-icon"
            @click="handleAddData"
          />
        </div>
      </div> -->
      <div class="btn-container flex-row align-items-center justify-content-between">
        <div class="bk-button-group bk-button-group-cls">
          <bk-button
            v-for="(panel, index) in panels"
            :key="index"
            :class="processNameActive === panel.name ? 'is-selected' : ''"
            @click="handleBtnGroupClick(panel.name, index)">
            {{ panel.name }}
            <i
              v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
              class="paasng-icon paasng-edit-2 pl5 pr5"
              ref="tooltipsHtml"
              @click="handleProcessNameEdit(panel.name, index)"
              v-bk-tooltips="$t('编辑')"
            />

            <i
              v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
              class="paasng-icon paasng-icon-close item-close-icon"
              v-bk-tooltips="$t('删除')"
              @click.stop="handleDelete(panel.name, index)"
            />
          </bk-button>
          <span v-if="isPageEdit" class="pl10">
            <bk-button
              text theme="primary"
              @click="handleProcessNameEdit('')">
              <i class="paasng-icon paasng-plus-thick add-icon" />
              {{ $t('新增进程') }}
            </bk-button>
          </span>
        </div>
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
      <div class="form-deploy" v-if="isPageEdit">
        <div
          class="create-item"
          data-test-id="createDefault_item_baseInfo"
        >
          <bk-form
            ref="formDeploy"
            :model="formData"
            :rules="rules"
            ext-cls="form-process"
          >
            <bk-form-item
              :label="$t('容器镜像地址')"
              :required="true"
              :label-width="120"
              :property="'image'"
            >
              <bk-input
                ref="mirrorUrl"
                v-model="formData.image"
                style="width: 500px;"
                :placeholder="$t('请输入带标签的镜像地址')"
              />
              <p class="whole-item-tips">
                {{ $t('示例镜像：') }}
                <span>
                  {{ GLOBAL.CONFIG.MIRROR_EXAMPLE }}
                </span>
                &nbsp;
                <span
                  class="whole-item-tips-text"
                  @click.stop="useExample"
                >{{ $t('使用示例镜像') }}</span>
              </p>
              <p :class="['whole-item-tips', localLanguage === 'en' ? '' : 'no-wrap']">
                <span>{{ $t('镜像应监听“容器端口”处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>&nbsp;
                <a
                  target="_blank"
                  :href="GLOBAL.DOC.BUILDING_MIRRIRS_DOC"
                >{{ $t('帮助：如何构建镜像') }}</a>
              </p>
            </bk-form-item>

            <!-- 镜像凭证 -->
            <bk-form-item
              v-if="panels[panelActive]"
              :label="$t('镜像凭证')"
              :label-width="120"
              :property="'command'"
            >
              <bk-select
                v-model="bkappAnnotations[imageCrdlAnnoKey]"
                :disabled="false"
                style="width: 500px;"
                ext-cls="select-custom"
                ext-popover-cls="select-popover-custom"
                searchable
              >
                <bk-option
                  v-for="option in imageCredentialList"
                  :id="option.name"
                  :key="option.name"
                  :name="option.name"
                />
                <div
                  slot="extension"
                  style="cursor: pointer;"
                  @click="handlerCreateImageCredential"
                >
                  <i class="bk-icon icon-plus-circle mr5" />{{ $t('新建凭证') }}
                </div>
              </bk-select>
              <p class="whole-item-tips">
                {{ $t('私有镜像需要填写镜像凭证才能拉取镜像') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('启动命令')"
              :label-width="120"
              :property="'command'"
            >
              <bk-tag-input
                v-model="formData.command"
                style="width: 500px"
                ext-cls="tag-extra"
                :placeholder="$t('留空将使用镜像的默认 entry point 命令')"
                :allow-create="allowCreate"
                :allow-auto-match="true"
                :has-delete-icon="hasDeleteIcon"
                :paste-fn="copyStartMommand"
              />
              <p class="whole-item-tips">
                {{ $t('示例：start_server，多个命令可用回车键分隔') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('命令参数')"
              :label-width="120"
              :property="'args'"
            >
              <bk-tag-input
                v-model="formData.args"
                style="width: 500px"
                ext-cls="tag-extra"
                :placeholder="$t('请输入命令参数')"
                :allow-create="allowCreate"
                :allow-auto-match="true"
                :has-delete-icon="hasDeleteIcon"
                :paste-fn="copyCommandParameter"
              />
              <p class="whole-item-tips">
                {{ $t('示例：--env prod，多个参数可用回车键分隔') }}
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('容器端口')"
              :label-width="120"
              :property="'targetPort'"
            >
              <bk-input
                v-model="formData.targetPort"
                style="width: 500px"
                :placeholder="$t('请输入 1 - 65535 的整数，非必填')"
              />
              <i
                v-show="isTargetPortErrTips"
                v-bk-tooltips.top-end="targetPortErrTips"
                class="bk-icon icon-exclamation-circle-shape tooltips-icon"
                tabindex="0"
                style="right: 8px;"
              />
              <p class="whole-item-tips">
                {{ $t('请求将会被发往容器的这个端口。推荐不指定具体端口号，让容器监听 $PORT 环境变量') }}
              </p>
            </bk-form-item>
            <bk-form-item :label-width="40">
              <bk-button
                text
                theme="primary"
                title="更多配置"
                @click="ifopen = !ifopen">
                {{ $t('更多配置') }}
                <i
                  class="paasng-icon"
                  :class="ifopen ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
                />
              </bk-button>
            </bk-form-item>
            <bk-form-item
              v-if="ifopen"
              :label="$t('配置环境')"
              :label-width="120"
            >
              <bk-radio-group v-model="envName">
                <bk-radio-button
                  class="radio-cls"
                  v-for="(item, index) in envsData"
                  :key="index"
                  :value="item.value">
                  {{ item.label }}
                </bk-radio-button>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="ifopen"
              :label-width="120"
            >
              <div class="env-container">
                <bk-form
                  ref="formEnv"
                  :model="formData"
                  ext-cls="form-envs"
                >
                  <bk-form-item
                    :label="$t('资源配额方案')"
                    :label-width="120"
                  >
                    <bk-select
                      v-model="formData.resQuotaPlan"
                      allow-create
                      :disabled="false"
                      style="width: 150px;"
                      searchable
                    >
                      <bk-option
                        v-for="option in resQuotaData"
                        :id="option"
                        :key="option"
                        :name="option"
                      />
                    </bk-select>
                  </bk-form-item>
                  <bk-form-item
                    :label="$t('扩缩容方式')"
                    :label-width="120"
                  >
                    <bk-radio-group v-model="isAutoscaling" @change="handleRadioChange">
                      <bk-radio-button class="radio-cls" :value="false">
                        {{ $t('手动调节') }}
                      </bk-radio-button>
                      <bk-radio-button
                        class="radio-cls" :value="true">
                        {{ $t('自动调节') }}
                      </bk-radio-button>
                    </bk-radio-group>
                  </bk-form-item>
                  <section v-if="isAutoscaling" class="mt20">
                    <bk-form-item
                      :label="$t('最小副本数')"
                      :label-width="120"
                      :required="true"
                      :property="'autoscaling.minReplicas'"
                      :rules="rules.minReplicas">
                      <bk-input
                        v-model="formData.autoscaling.minReplicas"
                        type="number"
                        :max="5"
                        :min="1"
                        style="width: 150px"
                      />
                    </bk-form-item>
                    <bk-form-item
                      :label="$t('最大副本数')"
                      :label-width="120"
                      :required="true"
                      :property="'autoscaling.maxReplicas'"
                      :rules="rules.maxReplicas">
                      <bk-input
                        v-model="formData.autoscaling.maxReplicas"
                        type="number"
                        :max="5"
                        :min="1"
                        style="width: 150px"
                      />
                    </bk-form-item>
                  </section>
                  <section v-else class="mt20">
                    <bk-form-item
                      :label="$t('副本数量')"
                      :label-width="120"
                      :required="true"
                      :property="'replicas'"
                      :rules="rules.replicas"
                    >
                      <bk-input
                        v-model="formData.replicas"
                        type="number"
                        :max="5"
                        :min="1"
                        style="width: 150px"
                      />
                    </bk-form-item>
                  </section>
                </bk-form>
              </div>
            </bk-form-item>
          </bk-form>
        </div>

        <!-- <div class="form-resource">
          <div class="item-title">
            {{ $t('副本数和资源') }}
          </div>
          <bk-form
            ref="formResource"
            :model="formData"
            form-type="inline"
            style="padding-left: 30px"
          >
            <bk-form-item
              :label="$t('副本数量')"
              :required="true"
              :property="'replicas'"
              class="mb20"
              :rules="rules.replicas"
            >
              <bk-input
                v-model="formData.replicas"
                type="number"
                :max="5"
                :min="1"
                style="width: 150px"
              />
            </bk-form-item>
            <br>
            <bk-form-item
              class="pl20"
              :label="$t('内存')"
              :property="'memory'"
            >
              <bk-select
                v-model="formData.memory"
                allow-create
                :disabled="false"
                style="width: 150px;"
                searchable
              >
                <bk-option
                  v-for="option in memoryData"
                  :id="option.value"
                  :key="option.key"
                  :name="option.value"
                />
              </bk-select>
              <span class="whole-item-tips">{{ $t('每个容器能使用的最大内存') }}</span>
            </bk-form-item>
            <bk-form-item
              :label="$t('CPU(核数)')"
              :property="'cpu'"
            >
              <bk-select
                v-model="formData.cpu"
                allow-create
                :disabled="false"
                style="width: 150px;"
                searchable
              >
                <bk-option
                  v-for="option in cpuData"
                  :id="option.value"
                  :key="option.key"
                  :name="option.value"
                />
              </bk-select>
              <span class="whole-item-tips">{{ $t('每个容器能使用的CPU核心数量') }}</span>
            </bk-form-item>
          </bk-form>
        </div> -->
      </div>

      <!-- 查看态 -->
      <div class="form-detail mt20" v-else>
        <bk-form
          ref="formDeploy"
          :model="formData">
          <bk-form-item
            :label="$t('容器镜像地址：')">
            <span class="form-text">{{ formData.image || '--' }}</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('容器镜像地址：')">
            <span class="form-text">{{ bkappAnnotations[imageCrdlAnnoKey] || '--' }}</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('启动命令：')">
            <span class="form-text">
              {{ formData.command.length ? formData.command.join(',') : '--' }}
            </span>
          </bk-form-item>
          <bk-form-item
            :label="$t('命令参数：')">
            <span class="form-text">
              {{ formData.args.length ? formData.args.join(',') : '--' }}
            </span>
          </bk-form-item>
          <bk-form-item
            :label="$t('容器端口：')">
            <span class="form-text">{{ formData.targetPort || '--' }}</span>
          </bk-form-item>
          <bk-form-item :label-width="50">
            <bk-button
              text
              theme="primary"
              title="更多配置"
              @click="ifopen = !ifopen">
              {{ $t('更多配置') }}
              <i
                class="paasng-icon"
                :class="ifopen ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
              />
            </bk-button>
          </bk-form-item>
          <section class="mt20" v-if="ifopen">
            <bk-form-item
              :label="$t('配置环境：')">
              <span class="form-text">{{ ENV_ENUM[envName] || '--' }}</span>
            </bk-form-item>
            <bk-form-item
              :label="$t('资源配额方案：')">
              <span class="form-text">{{ formData.resQuotaPlan || '--' }}</span>
            </bk-form-item>
            <bk-form-item
              :label="$t('扩缩容方式：')">
              <span class="form-text">{{ isAutoscaling ? $t('自动调节') : $t('手动调节') }}</span>
            </bk-form-item>
            <!-- <bk-form-item
              :label="$t('触发条件：')">
              <span class="form-text">{{ formData.targetPort || '--' }}</span>
            </bk-form-item> -->
            <section v-if="isAutoscaling" class="mt20">
              <bk-form-item
                :label="$t('最小副本数：')">
                <span class="form-text">{{ formData.autoscaling.minReplicas || '--' }}</span>
              </bk-form-item>
              <bk-form-item
                :label="$t('最大副本数：')">
                <span class="form-text">{{ formData.autoscaling.maxReplicas || '--' }}</span>
              </bk-form-item>
            </section>
            <section v-else class="mt20">
              <bk-form-item
                :label="$t('副本数量：')">
                <span class="form-text">{{ formData.replicas || '--' }}</span>
              </bk-form-item>
            </section>
          </section>
        </bk-form>
      </div>
    </div>

    <bk-dialog
      v-model="processDialog.visiable"
      width="320"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :title="processDialog.title"
      @confirm="handleConfirm"
      @cancel="processDialog.visiable = false"
    >
      <bk-input
        class="path-input-cls"
        v-model="processDialog.name"
        :placeholder="$t('请输入')"></bk-input>
    </bk-dialog>
  </paas-content-loader>
</template>

<script>import _ from 'lodash';
import { bus } from '@/common/bus';
import { RESQUOTADATA, ENV_ENUM } from '@/common/constants';

export default {
  components: {
  },
  props: {
    moduleId: {
      type: String,
      default: '',
    },
    cloudAppData: {
      type: Object,
      default: {},
    },
  },
  data() {
    return {
      panels: [],
      processNameActive: 'web',   // 选中的进程名
      btnIndex: 0,
      showEditIconIndex: null,
      iconIndex: '',
      panelActive: 0,
      formData: {
        image: '',
        name: '',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        replicas: 1,
        targetPort: 8080,
        autoscaling: { minReplicas: '', maxReplicas: '' },
      },
      bkappAnnotations: {},
      command: [],
      args: [],
      allowCreate: true,
      hasDeleteIcon: true,
      processData: [],
      localCloudAppData: {},
      memoryData: [
        { key: '256 Mi', value: '256Mi' },
        { key: '512 Mi', value: '512Mi' },
        { key: '1024 Mi', value: '1024Mi' },
      ],
      cpuData: [
        { key: '500m', value: '500m' },
        { key: '1000m', value: '1000m' },
        { key: '2000m', value: '2000m' },
      ],
      hooks: null,
      isLoading: true,
      rules: {
        image: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            regex: /^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$/,
            message: this.$t('地址格式不正确'),
            trigger: 'blur',
          },
        ],
        replicas: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur',
          },
          {
            min: 1,
            message: this.$t('有效值范围1-5'),
            trigger: 'blur',
          },
          {
            max: 5,
            message: this.$t('有效值范围1-5'),
            trigger: 'blur',
          },
        ],
        minReplicas: [
          {
            required: true,
            message: this.$t('请填写最小副本数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: this.$t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator: (v) => {
              const minReplicas = Number(v);
              const maxReplicas = Number(this.formData.autoscaling.maxReplicas);
              return minReplicas <= maxReplicas;
            },
            message: () => `${this.$t('最小副本数不可大于最大副本数')}`,
            trigger: 'blur',
          },
        ],
        maxReplicas: [
          {
            required: true,
            message: this.$t('请填写最大副本数'),
            trigger: 'blur',
          },
          {
            regex: /^[1-9][0-9]*$/,
            message: this.$t('请填写大于0的整数'),
            trigger: 'blur',
          },
          {
            validator: (v) => {
              const maxReplicas = Number(v);
              const minReplicas = Number(this.formData.autoscaling.minReplicas);
              return maxReplicas >= minReplicas;
            },
            message: `${this.$t('最大副本数不可小于最小副本数')}`,
            trigger: 'blur',
          },
        ],
      },
      isBlur: true,
      imageCredential: '',
      imageCredentialList: [],
      targetPortErrTips: '',
      isTargetPortErrTips: false,
      ifopen: true,
      envsData: [{ value: 'stag', label: this.$t('预发布环境') }, { value: 'prod', label: this.$t('生产环境') }],
      resQuotaData: RESQUOTADATA,
      isAutoscaling: false,
      btnMouseIndex: '',
      processDialog: {
        visiable: false,
        title: this.$t('进程名称'),
        name: '',
        index: '',
      },
      envOverlayData: { replicas: [] },
      envName: 'stag',
      ENV_ENUM,
      localProcessNameActive: '',
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    appCode() {
      return this.$route.params.id;
    },
    imageCrdlAnnoKey() {
      return `bkapp.paas.bk.tencent.com/image-credentials.${this.processNameActive}`;
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
          this.envOverlayData = this.localCloudAppData.spec.envOverlay || {};
          this.processData = val.spec.processes;
          this.formData = this.processData[this.btnIndex];
          console.log('this.formData', this.formData);
          this.bkappAnnotations = this.localCloudAppData.metadata.annotations;
        }
        this.panels = _.cloneDeep(this.processData);
      },
      immediate: true,
      deep: true,
    },
    formData: {
      handler(val) {
        if (this.localCloudAppData.spec) {
          val.name = this.processNameActive;
          val.replicas = val.replicas && Number(val.replicas);
          if (val.targetPort && /^\d+$/.test(val.targetPort)) { // 有值且为数字字符串
            val.targetPort = Number(val.targetPort);
          }

          // 更多配置信息
          const processConfig = (this.envOverlayData?.resQuotas || []).find(e => e.process === this.processNameActive);
          this.envName = processConfig ? processConfig.envName : 'stag';

          // 如果没有自动调节相关数据结构 则前端需要做兼容处理
          this.isAutoscaling = !!val.autoscaling;

          // 如果没有资源配额方案数据 前端也需要做兼容处理
          if (!val.resQuotaPlan) {
            val.resQuotaPlan = 'default';
          }

          this.$set(this.localCloudAppData.spec.processes, this.btnIndex, val);   // 赋值数据给选中的进程
          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        }
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      },
      immediate: true,
      // deep: true,
    },
    bkappAnnotations: {
      handler(val) {
        if (val[this.imageCrdlAnnoKey]) {
          this.$set(this.localCloudAppData.metadata, 'annotations', val);
          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        } else {
          delete val[this.imageCrdlAnnoKey];
        }
      },
      deep: true,
    },
    'formData.targetPort'(value) {
      if (value === null || value === '') {
        this.isTargetPortErrTips = false;
        return false;
      }
      if (value) {
        if (isNaN(Number(value))) {
          this.isTargetPortErrTips = true;
          this.targetPortErrTips = this.$t('只能输入数字');
        } else {
          if (!(value >= 1 && value <= 65535)) {
            this.isTargetPortErrTips = true;
            this.targetPortErrTips = this.$t('端口有效范围1-65535');
          } else {
            this.isTargetPortErrTips = false;
          }
        }
      }
    },

    panels: {
      handler(val) {
        if (!val.length) return;
        const isDisabled = val[this.panelActive].isEdit;
        bus.$emit('release-disabled', isDisabled);
      },
      deep: true,
    },

    'formData.autoscaling.maxReplicas'(val) {
      if (val && val >= this.formData.autoscaling.minReplicas) {
        this.$refs.formEnv?.clearError();
      }
    },
    'formData.autoscaling.minReplicas'(val) {
      if (val && val <= this.formData.autoscaling.maxReplicas) {
        this.$refs.formEnv?.clearError();
      }
    },
  },
  created() {
    this.getImageCredentialList();
  },
  mounted() {
    this.$refs.mirrorUrl?.focus();
    setTimeout(() => {
      this.isAutoscaling = !!this.formData.autoscaling;
    }, 1000);
  },
  methods: {
    handlePanelClick(i, e, isAdd) {
      this.panelActive = i;
      this.formData = this.processData[i] || {
        name: this.itemValue,
        image: '',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        replicas: 1,
        targetPort: null,
      };
      if (e && e.target === document.querySelector('.bk-input-cls input')) {
        this.$nextTick(() => {
          this.$set(this.panels[i], 'isEdit', true);
        });
      } else {
        !isAdd && this.$refs.mirrorUrl.focus();
      }
      // tab切换清除提示
      this.$refs.formDeploy.clearError();
      this.$refs.formResource.clearError();
    },
    handlePanelEnter(i) {
      if (i === 0) return;
      this.showEditIconIndex = i;
    },
    handlePanelLeave() {
      this.showEditIconIndex = null;
    },
    handleIconClick(i) {
      this.resetData();
      this.panels[i].isEdit = true;
      this.iconIndex = i;
      this.itemValue = this.panels[i].name;
      this.handlePanelClick(i, null, 'add');
      setTimeout(() => {
        this.$refs.panelInput && this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
      }, 500);
    },

    // 鼠标失去焦点
    handleBlur() {
      console.log('this.panels[this.iconIndex]', this.panels[this.iconIndex]);
      if (this.panels[this.iconIndex]) { // 编辑
        if (!this.itemValue) {
          this.panels.splice(this.iconIndex, 1);
        } else {
          const canHandel = this.handleRepeatData(this.iconIndex);
          if (!canHandel) return;
          this.panels[this.iconIndex].name = this.itemValue;
        }
      } else { // 新增
        const canHandel = this.handleRepeatData();
        if (!canHandel) return;
        if (!this.itemValue) {
          this.panels.splice(this.panels.length - 1, 1);
        } else {
          this.panels[this.panels.length - 1].name = this.itemValue;
          this.handlePanelClick(this.panels.length - 1);
        }
      }
      this.panels = this.panels.map((e) => {
        e.isEdit = false;
        return e;
      });
    },

    // 处理重复添加和正则
    handleRepeatData(index) {
      if (!this.isBlur) return;
      this.isBlur = false; // 处理enter会触发两次的bug
      let { panels } = this;
      if (index) {
        panels = this.panels.filter((e, i) => i !== index);
      }
      const panelName = panels.map(e => e.name);
      if (this.itemValue !== 'name' && panelName.includes(this.itemValue)) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('不允许添加同名进程'),
        });
        setTimeout(() => {
          this.isBlur = true;
          this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
        }, 100);
        return false;
      } if (!/^[a-z0-9]([-a-z0-9]){1,11}$/.test(this.itemValue)) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请输入 2-12 个字符的小写字母、数字、连字符，以小写字母开头'),
        });
        setTimeout(() => {
          this.isBlur = true;
          this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
        }, 100);
        return false;
      }
      setTimeout(() => {
        this.isBlur = true;
      }, 100);

      return true;
    },

    // 处理回车
    handleEnter() {
      this.handleBlur();
    },

    // 点击icon新增数据
    handleAddData() {
      this.iconIndex = '';
      this.resetData();
      this.panels.push({
        name: 'name',
        isEdit: true,
      });
      this.itemValue = 'name';
      this.panelActive = this.panels.length - 1;
      this.handlePanelClick(this.panelActive, null, 'add');
      setTimeout(() => {
        this.$refs.panelInput[0] && this.$refs.panelInput[0].focus();
      }, 100);
    },

    resetData() {
      this.panels.forEach((element) => {
        element.isEdit = false;
      });
    },

    async formDataValidate(index) {
      try {
        await this.$refs.formResource.validate();
        await this.$refs.formDeploy.validate();
        if (index) {
          this.handlePanelValidateSwitch(index);
        }
        return true;
      } catch (error) {
        console.error(error);
        return false;
      }
    },

    // 切换至未符合规则的Panel
    handlePanelValidateSwitch(i) {
      this.panelActive = i;
      this.formData = this.localCloudAppData.spec.processes[i] || {
        image: '',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        replicas: 1,
        targetPort: 8080,
      };
      this.$refs.mirrorUrl.focus();
    },

    trimStr(str) {
      return str.replace(/(^\s*)|(\s*$)/g, '');
    },

    // 启动命令复制
    copyStartMommand(val) {
      const value = this.trimStr(val);
      if (!value) {
        this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
        return [];
      }
      const commandArr = value.split(',');
      commandArr.forEach((item) => {
        if (!this.formData.command.includes(item)) {
          this.formData.command.push(item);
        }
      });
      return this.formData.command;
    },

    copyCommandParameter(val) {
      const value = this.trimStr(val);
      if (!value) {
        this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
        return [];
      }
      const commandArr = value.split(',');
      commandArr.forEach((item) => {
        if (!this.formData.args.includes(item)) {
          this.formData.args.push(item);
        }
      });
      return this.formData.args;
    },

    useExample() {
      this.formData.image = this.GLOBAL.CONFIG.MIRROR_EXAMPLE;
      if (this.GLOBAL.CONFIG.MIRROR_EXAMPLE === 'nginx:latest') {
        this.formData.command = [];
        this.formData.args = [];
        this.formData.targetPort = 80;
        return;
      }
      this.formData.command = ['bash', '/app/start_web.sh'];
      this.formData.args = [];
      this.formData.targetPort = 5000;
    },

    // 获取凭证列表
    async getImageCredentialList() {
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode });
        this.imageCredentialList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    // 前往创建镜像凭证页面
    handlerCreateImageCredential() {
      this.$router.push({ name: 'imageCredential' });
    },

    // 按扭组点击
    handleBtnGroupClick(v, i) {
      // 选中的进程信息
      this.formData = this.localCloudAppData.spec.processes[i];
      this.localProcessNameActive = v;    // 点击的tab名，编辑数据时需要用到
      this.processNameActive = v;
      this.btnIndex = i;
    },

    // 编辑
    handleEditClick() {
      this.$store.commit('cloudApi/updatePageEdit', true);
    },

    // 处理保存时数据问题
    handleProcessData() {
      // 保存时数据格式应该是用envOverlay提交
      // 副本数量相关数据
      const replicasData = {
        envName: this.envName,
        process: this.processNameActive,
        count: this.formData.replicas,
      };
      // 资源配置相关数据
      const resQuotaPlanData = {
        envName: this.envName,
        process: this.processNameActive,
        plan: this.formData.resQuotaPlan,
      };
      console.log('resQuotaPlanData', resQuotaPlanData);

      if (!this.localCloudAppData.spec.envOverlay) {
        this.localCloudAppData.spec.envOverlay = {};
      }

      if (this.formData.replicas) {     // 副本数量
        console.log('this.localCloudAppData.spec', this.localCloudAppData);
        // 没有replicas时
        if (!this.localCloudAppData.spec.envOverlay?.replicas) {
          this.localCloudAppData.spec.envOverlay.replicas = [];
          this.localCloudAppData.spec.envOverlay.replicas.push(replicasData);
        } else {
          // 有replicas数据
          const replicasProcess = this.localCloudAppData.spec.envOverlay.replicas.map(e => e.process);
          this.localCloudAppData.spec.envOverlay.replicas.forEach((e) => {
            if (e.process === replicasData.process) {
              e.envName = replicasData.envName;
              e.count = replicasData.count;
            } else {
              if (!replicasProcess.includes(replicasData.process)) {
                this.localCloudAppData.spec.envOverlay.replicas.push(replicasData);
              }
            }
          });
        }
      }
      // 自动调节
      if (this.isAutoscaling) {
        // 自动调节相关数据
        delete this.localCloudAppData.spec.envOverlay.replicas;
        const autoscalingData = {
          envName: this.envName,
          process: this.processNameActive,
          policy: 'default',
          minReplicas: this.formData.autoscaling.minReplicas ? Number(this.formData.autoscaling.minReplicas) : '',
          maxReplicas: this.formData.autoscaling.maxReplicas ? Number(this.formData.autoscaling.maxReplicas) : '',
        };
        // 没有autoscaling时
        if (!this.localCloudAppData.spec.envOverlay?.autoscaling?.length) {
          this.localCloudAppData.spec.envOverlay.autoscaling = [];
          this.localCloudAppData.spec.envOverlay.autoscaling.push(autoscalingData);
        } else {
          // 有autoscaling数据
          // const autoscalingProcess = this.localCloudAppData.spec.envOverlay.autoscaling.map(e => e.process) || [];
          // this.localCloudAppData.spec.envOverlay.autoscaling
          //   .forEach((e) => {
          //     if (e.process === autoscalingData.process) {
          //       e.envName = autoscalingData.envName;
          //       e.minReplicas =  autoscalingData.minReplicas;
          //       e.maxReplicas = autoscalingData.maxReplicas;
          //     } else {
          //       console.log(autoscalingProcess, autoscalingData, autoscalingData.process);
          //       if (!autoscalingProcess.includes(autoscalingData.process)) {   // 如果没包含就需要添加一条数据
          //         this.localCloudAppData.spec.envOverlay.autoscaling.push(autoscalingData);
          //         console.log('this.localCloudAppData.spec.envOverlay.autoscaling', this.localCloudAppData.spec.envOverlay.autoscaling);
          //       }
          //     }
          //   });
        }
        // delete this.localCloudAppData.spec.envOverlay && this.localCloudAppData.spec.envOverlay.autoscaling;
      } else { // // 手动调节
        // 需要删除当前进程base中的autoscaling
        delete this.localCloudAppData.spec.processes[this.btnIndex].autoscaling;
        // 过滤当前进程当前环境envOverlay中autoscaling
        const { envOverlay } = this.localCloudAppData.spec;
        this.handleFilterAutoscalingData(envOverlay, this.processNameActive);  // 传入envOverlay、当前进程名
      }

      // 资源配额方案
      if (!this.localCloudAppData.spec.envOverlay?.resQuotas) { // 没有resQuotas时
        this.localCloudAppData.spec.envOverlay.resQuotas = [];
        this.localCloudAppData.spec.envOverlay.resQuotas.push(resQuotaPlanData);
      } else {
        const resQuotasProcess = this.localCloudAppData.spec.envOverlay.resQuotas.map(e => e.process) || [];
        this.localCloudAppData.spec.envOverlay.resQuotas
          .forEach((e) => {
            if (e.process === resQuotaPlanData.process) {
              e.envName = resQuotaPlanData.envName;
              e.plan = resQuotaPlanData.plan;
            } else {
              if (!resQuotasProcess.includes(resQuotaPlanData.process)) {   // 如果没包含就需要添加一条数据
                this.localCloudAppData.spec.envOverlay.resQuotas.push(resQuotaPlanData);
              }
            }
          });
      }

      // 将最大值最小值改为数字类型提交
      (this.localCloudAppData.spec?.processes || []).forEach((e) => {
        if (e.autoscaling) {
          e.autoscaling.minReplicas = e.autoscaling.minReplicas ? Number(e.autoscaling.minReplicas) : '';
          e.autoscaling.maxReplicas = e.autoscaling.maxReplicas ? Number(e.autoscaling.maxReplicas) : '';
        }
      });

      console.log('this.localCloudAppData.spec.envOverlay', this.localCloudAppData.spec.envOverlay);
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
    },

    // 处理自动调节问题
    handleRadioChange(v) {
      this.$refs.formEnv?.clearError();
      if (v && !this.formData.autoscaling) {
        this.formData.autoscaling = {
          maxReplicas: '',
          minReplicas: '',
          policy: 'default',
        };
      }
    },

    // 弹窗确认
    handleConfirm() {
      if (this.processDialog.index) {   // 编辑进程名
        this.panels.forEach((e, i) => {
          if (i === this.processDialog.index) {
            e.name = this.processDialog.name;
          }
        });
        console.log('this.localCloudAppData.spec', this.localCloudAppData.spec, this.localProcessNameActive);
        this.localCloudAppData.spec.processes[this.btnIndex].name = this.processDialog.name; // 需要更新cloudAppData

        // 需要更新外层envOverlay中的自动调节数据
        (this.localCloudAppData.spec?.envOverlay?.autoscaling || []).map((e) => {
          if (e.process === this.localProcessNameActive) {
            e.process = this.processDialog.name;
          }
          return e;
        });

        // 需要更新外层envOverlay中配额数据
        (this.localCloudAppData.spec?.envOverlay?.resQuotas || []).map((e) => {
          if (e.process === this.localProcessNameActive) {
            e.process = this.processDialog.name;
          }
          return e;
        });

        // this.handleBtnGroupClick(this.processDialog.name);
      } else {  // 新增进程
        this.panels.push({ name: this.processDialog.name });
        console.log('this.panels111', this.panels);
        this.btnIndex = this.panels.length - 1;
        this.formData = {
          name: this.processDialog.name,
          image: '',
          command: [],
          args: [],
          memory: '256Mi',
          cpu: '500m',
          replicas: 1,
          targetPort: null,
          envOverlay: {
            replicas: [],
          },
          autoscaling: { policy: 'default' },
        };
        this.localCloudAppData.spec.processes.push(this.formData);
      }
      console.log('this.panels', this.panels, this.formData, this.localCloudAppData);
      // debugger;
      this.processNameActive = this.processDialog.name; // 选中当前点击tab
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
      this.processDialog.visiable = false;
    },

    // 编辑进程名称
    handleProcessNameEdit(processName, i = '') {
      this.processDialog.visiable = true;
      this.processDialog.name = processName;
      this.processDialog.index = i;   // 如果为空 这代表是新增
    },

    // 删除某个进程
    handleDelete(processName, i = '') {
      console.log('this.processNameActive', this.processNameActive);
      // eslint-disable-next-line prefer-destructuring
      this.formData = this.processData[0];
      this.localCloudAppData.spec.processes.splice(i, 1);

      // 过滤外层envOverlay中的自动调节数据
      this.localCloudAppData.spec.envOverlay.autoscaling = (this.localCloudAppData.spec.envOverlay.autoscaling || [])
        .filter(e => e.process !== this.processNameActive);

      // 过滤外层envOverlay中配额数据
      this.localCloudAppData.spec.envOverlay.resQuotas = (this.localCloudAppData.spec.envOverlay.resQuotas || [])
        .filter(e => e.process !== this.processNameActive);

      // 过滤外层envOverlay中副本数量
      this.localCloudAppData.spec.envOverlay.replicas = (this.localCloudAppData.spec.envOverlay?.replicas || [])
        .filter(e => e.process !== this.processNameActive);

      this.processData = this.localCloudAppData.spec.processes;
      this.panels = _.cloneDeep(this.processData);
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);

      this.processNameActive = 'web';
      this.btnIndex = 0;
    },

    // 过滤当前进程当前环境envOverlay中autoscaling
    handleFilterAutoscalingData(data, process) {
      this.localCloudAppData.spec.envOverlay.autoscaling = (data?.autoscaling || [])
        .filter(e => !(e.process === process));
    },
  },
};
</script>
<style lang="scss" scoped>
    .process-container{
        // margin-top: 20px;
        // border: 1px solid #e6e9ea;
        border-top: none;
        padding-bottom: 20px;
    }
    .tab-container {
        position: relative;
        line-height:50px;
        height: 50px;
        .tab-list {
            display: flex;
            align-items: center;
            background: #FAFBFD;
            border: 1px solid #DCDEE5;
            border-left: none;
            border-right: none;
            height: 52px;
            .tab-item{
                padding: 0 18px;
                border-right: 1px solid #dcdee5;
                cursor: pointer;
                position: relative;
            }
            .tab-item :hover {
                background: #fff;
            }
            .edit-name-icon {
                cursor: pointer;
            }
            .isActive{
                border-bottom: 2px solid #fff;
                border-top: 1px solid #dcdee5;
                background: #fff;
                color: #3a84ff;
                cursor: default;
            }
            .add-icon{
                font-size: 18px;
                padding-left: 10px;
                cursor: pointer;
            }
        }
    }
    .tab-container .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item{
        padding: 0 18px;
        margin-right: 0px;
    }

    .form-deploy{
        margin: 20px 40px;
        .item-title{
            font-weight: Bold;
            font-size: 14px;
            color: #313238;
            margin: 24px 0;
        }
        .whole-item-tips{
            line-height: 26px;
            color: #979ba5;
            font-size: 12px;
            .whole-item-tips-text {
                color: #3a84ff;
                &:hover {
                    cursor: pointer;
                }
            }
        }
        .no-wrap {
            position: relative;
            width: 600px;
        }
        .create-item{
            padding-bottom: 10px;
            border-bottom: 1px solid #DCDEE5;
           .form-group-dir{
            display: flex;
            .form-label {
                color: #63656e;
                line-height: 32px;
                font-size: 14px;
                padding-top: 10px;
                width: 90px;
                text-align: right;
                margin-right: 10px;
            }
            .form-group-flex{
                width: 520px;
                margin-top: 10px;
            }
           }
        }
        .form-resource{
           .form-resource-flex{
                display: flex;
           }
        }

        .form-pre {
            border-top: 1px solid #DCDEE5;
        }

        .form-pre-command.bk-form.bk-inline-form .bk-form-input {
            height: 32px !important;
        }

        .form-process{
            width: 625px;
        }
    }
    .btn-container{
      padding: 0 24px;
      .bk-button-group-cls{
        display: flex !important;
        align-items: center;
         .item-close-icon{
            position: absolute;
            top: -1px;
            right: 0px;
            font-size: 20px;
            color: #ea3636;
            cursor: pointer;
        }
      }
    }
    .form-detail{
      .form-text{
        color: #313238;
      }
    }
    .env-container{
      width: 785px;
      background: #F5F7FA;
      border-radius: 2px;
      padding: 20px 24px;
    }
    .process-name{
      width: 280px;
      height: 140px;
    }

    .form-envs{
      /deep/ .tooltips-icon{
        right: 440px !important;
        top: 7px !important;
      }
    }
</style>
