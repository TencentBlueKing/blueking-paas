<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-process-loading"
    :offset-top="20"
    :offset-left="20"
    class="deploy-action-box"
  >
    <div class="process-container">
      <div class="btn-container flex-row align-items-baseline" :class="[isPageEdit? '' : 'justify-content-between']">
        <div class="bk-button-group bk-button-group-cls">
          <bk-button
            v-for="(panel, index) in panels"
            :key="index"
            :class="[processNameActive === panel.name ? 'is-selected' : '', 'mb10']"
            @click="handleBtnGroupClick(panel.name, index)">
            {{ panel.name }}
            <i
              v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
              class="paasng-icon paasng-edit-2 pl5 pr10"
              ref="tooltipsHtml"
              @click="handleProcessNameEdit(panel.name, index)"
              v-bk-tooltips="$t('编辑')"
            />


            <bk-popconfirm
              content="确认删除该进程"
              width="288"
              style="display: inline-block;"
              class="item-close-icon"
              trigger="click"
              @confirm="handleDelete(panel.name, index)">
              <i
                v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
                class="paasng-icon paasng-icon-close"
                v-bk-tooltips="$t('删除')"
              />
            </bk-popconfirm>
          </bk-button>
        </div>
        <span v-if="isPageEdit" class="pl10">
          <bk-button
            text theme="primary"
            @click="handleProcessNameEdit('')">
            <i class="paasng-icon paasng-plus-thick add-icon" />
            {{ $t('新增进程') }}
          </bk-button>
        </span>
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
              :label-width="120"
              v-if="isV1alpha2"
            >
              {{ buildData.image }}
            </bk-form-item>

            <bk-form-item
              :label="$t('容器镜像地址')"
              :required="true"
              :label-width="120"
              :property="'image'"
              v-else
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

            <bk-form-item
              :label="$t('镜像凭证')"
              :label-width="120"
              v-if="isV1alpha2"
            >
              {{ buildData.imagePullPolicy }}
            </bk-form-item>

            <!-- 镜像凭证 -->
            <bk-form-item
              v-if="panels[panelActive] && !isV1alpha2"
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
                @change="handleImageChange"
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
                {{ $t('示例： -listen $PORT，多个参数可用回车键分隔') }}
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
                {{ $t('接收HTTP请求的端口号．建议镜像直接监听$PORT环境变量不修改本值') }}
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
              v-show="ifopen"
              :label-width="120"
            >
              <div class="env-name">生产环境</div>
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
                    <div class="flex-row align-items-center">
                      <bk-select
                        v-model="formData.resQuotaPlan"
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
                      <!-- tips内容不会双向绑定 需要重新渲染 -->
                      <i
                        v-if="quotaPlansFlag"
                        class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                      />
                      <i
                        v-else
                        class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                        v-bk-tooltips="tips"
                      />
                    </div>
                  </bk-form-item>
                  <bk-form-item
                    :label="$t('扩缩容方式')"
                    :label-width="120"
                  >
                    <section class="flex-row">
                      <bk-radio-group v-model="isAutoscaling" @change="handleRadioChange" style="flex: 1">
                        <bk-radio-button class="radio-cls" :value="false">
                          {{ $t('手动调节') }}
                        </bk-radio-button>
                        <bk-radio-button
                          class="radio-cls" :value="true">
                          {{ $t('自动调节') }}
                        </bk-radio-button>
                      </bk-radio-group>

                      <bk-alert type="info" v-if="isAutoscaling" style="margin-right: 60px;">
                        <span slot="title">
                          {{ $t('根据当前负载呵触发条件中设置的阈值自动扩缩容') }}
                          <a
                            target="_blank" :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/paas3_autoscaling'"
                            style="color: #3a84ff">
                            {{$t('查看动态扩缩容计算规则')}}
                          </a>
                        </span>
                      </bk-alert>
                    </section>
                  </bk-form-item>
                  <bk-form-item
                    v-if="isAutoscaling"
                    :label="$t('触发方式')"
                    :label-width="120"
                    class="desc-form-item">
                    <div class="desc-container flex-row">
                      <bk-select
                        v-model="cpuLabel"
                        disabled
                        style="width: 150px;"
                      >
                        <bk-option
                          v-for="option in triggerMethodData"
                          :id="option"
                          :key="option"
                          :name="option"
                        />
                      </bk-select>
                      <div class="mr10 ml10">
                        =
                      </div>
                      <bk-input
                        disabled
                        v-model="cpuValue"
                        style="width: 150px"
                      />
                      <!-- <p>
                        {{$t('响应时间')}} = 1000ms
                      </p> -->
                    </div>
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

      </div>

      <!-- 查看态 -->
      <div class="form-detail mt20" v-else>
        <bk-form
          :model="formData">
          <bk-form-item
            :label="$t('容器镜像地址：')">
            <span class="form-text">{{ isV1alpha2 ? buildData.image : (formData.image || '--') }}</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('镜像凭证：')">
            <span class="form-text">
              {{ isV1alpha2 ? buildData.imagePullPolicy : (bkappAnnotations[imageCrdlAnnoKey] || '--') }}
            </span>
          </bk-form-item>
          <bk-form-item
            :label="$t('启动命令：')">
            <span v-if="formData.command.length">
              <bk-tag v-for="item in formData.command" :key="item">{{ item }}</bk-tag>
            </span>
            <span class="form-text" v-else>--</span>
          </bk-form-item>
          <bk-form-item
            :label="$t('命令参数：')">
            <span v-if="formData.args.length">
              <bk-tag v-for="item in formData.args" :key="item">{{ item }}</bk-tag>
            </span>
            <span class="form-text" v-else>--</span>
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
      :loading="processDialog.loading"
      @confirm="handleConfirm"
      @cancel="handleDialogCancel"
    >
      <bk-form
        ref="formDialog"
        :model="processDialog"
        :label-width="0">
        <bk-form-item :required="true" :property="'name'" :rules="rules.processName">
          <bk-input
            class="path-input-cls"
            v-model="processDialog.name"
            :placeholder="$t('请输入进程名称')">
          </bk-input>
        </bk-form-item>
      </bk-form>
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
        autoscaling: { minReplicas: '', maxReplicas: '', policy: 'default' },
      },
      bkappAnnotations: {},
      command: [],
      args: [],
      allowCreate: true,
      hasDeleteIcon: true,
      processData: [],
      localCloudAppData: {},
      localCloudAppDataBackUp: {},
      hooks: null,
      isLoading: true,
      rules: {
        image: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur change',
          },
          {
            regex: /^(?:(?=[^:\\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$/,
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
        processName: [
          {
            required: true,
            message: this.$t('请输入进程名'),
            trigger: 'blur',
          },
          {
            validator: v => /^[a-z0-9]([-a-z0-9]){1,11}$/.test(v),
            message: `${this.$t('请输入 2-12 个字符的小写字母、数字、连字符，以小写字母开头')}`,
            trigger: 'blur',
          },
          {
            validator: (v) => {
              const panelName = this.panels.map(e => e.name);
              return !panelName.includes(v);
            },
            message: `${this.$t('不允许添加同名进程')}`,
            trigger: 'blur',
          },
        ],
      },
      isBlur: true,
      imageCredential: '',
      imageCredentialList: [],
      targetPortErrTips: '',
      isTargetPortErrTips: false,
      ifopen: false,
      envsData: [{ value: 'stag', label: this.$t('预发布环境') }, { value: 'prod', label: this.$t('生产环境') }],
      resQuotaData: RESQUOTADATA,
      isAutoscaling: false,
      btnMouseIndex: '',
      processDialog: {
        loading: false,
        visiable: false,
        title: this.$t('进程名称'),
        name: '',
        index: '',
      },
      envOverlayData: { replicas: [] },
      envName: 'stag',
      ENV_ENUM,
      localProcessNameActive: '',
      formDataBackUp: {
        autoscaling: {
          maxReplicas: '',
          minReplicas: 1,
          policy: 'default',
        },
        replicas: 1,
      },
      buildData: {},
      limit: {},
      request: {},
      quotaPlansFlag: false,
      triggerMethodData: ['CPU 使用率'],
      cpuLabel: 'CPU 使用率',
      cpuValue: '85%',
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
    imageLocalCrdlAnnoKey() {
      return `bkapp.paas.bk.tencent.com/image-credentials.${this.localProcessNameActive}`;
    },
    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit;
    },
    isV1alpha2() {
      return this.localCloudAppData?.apiVersion?.includes('v1alpha2');
    },

    tips() {
      return {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `
              <div>
                最大资源限制： <span>cpu：${this.limit.cpu} </span> <span>内存：${this.limit.memory} </span>
              </div>
              <div>
                最小资源请求：<span>cpu：${this.request.cpu} </span> <span>内存：${this.request.memory} </span>
              </div>
              `,
        placements: ['bottom'],
      };
    },
  },
  watch: {
    cloudAppData: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData = _.cloneDeep(val);
          this.localCloudAppDataBackUp = _.cloneDeep(this.localCloudAppData);
          this.envOverlayData = this.localCloudAppData.spec.envOverlay || {};
          this.buildData = this.localCloudAppData.spec.build || {};
          this.processData = val.spec.processes;
          this.formData = this.processData[this.btnIndex];
          this.isAutoscaling = !!(this.formData?.autoscaling?.minReplicas && this.formData?.autoscaling?.maxReplicas);
          this.bkappAnnotations = this.localCloudAppData.metadata.annotations;
        }
        this.panels = _.cloneDeep(this.processData);
      },
      immediate: true,
      // deep: true,
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


          this.$set(this.localCloudAppData.spec.processes, this.btnIndex, val);   // 赋值数据给选中的进程
          this.handleExtraConfig();   // 处理额外的配置

          // 扩缩容
          if (val?.autoscaling?.maxReplicas >= val?.autoscaling?.minReplicas) {
            this.$refs.formEnv?.clearError();
          }

          if (val?.autoscaling?.minReplicas <= val?.autoscaling?.maxReplicas) {
            this.$refs.formEnv?.clearError();
          }

          if (val?.image) {
            this.$refs.formDeploy?.clearError();
          }

          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        }
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      },
      immediate: true,
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

    'formData.resQuotaPlan'() {
      this.getQuotaPlans();
    },

    panels: {
      handler(val) {
        if (!val.length) return;
        const isDisabled = val[this.panelActive].isEdit;
        bus.$emit('release-disabled', isDisabled);
      },
      deep: true,
    },

    envName() {
      this.handleExtraConfig();   // 处理额外的配置
    },
  },
  created() {
    this.getImageCredentialList();
  },
  mounted() {
    setTimeout(() => {
      this.isAutoscaling = !!(this.formData?.autoscaling?.minReplicas && this.formData?.autoscaling?.maxReplicas);
    }, 1000);
  },
  methods: {
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
      this.isAutoscaling = !!(this.formData?.autoscaling?.minReplicas && this.formData?.autoscaling?.maxReplicas);
      this.localProcessNameActive = v;    // 点击的tab名，编辑数据时需要用到
      this.processNameActive = v;
      this.btnIndex = i;
    },

    // 编辑
    handleEditClick() {
      this.$store.commit('cloudApi/updatePageEdit', true);
    },

    // 处理保存时数据问题
    async handleProcessData() {
      try {
        await this.$refs.formEnv.validate();
        return true;
      } catch (error) {
        console.log('error', error);
        return false;
      }
    },

    // 处理自动调节问题
    handleRadioChange(v) {
      this.$refs.formEnv?.clearError();
      if (v) {
        this.$set(this.formData, 'autoscaling', this.formDataBackUp.autoscaling);
      } else {
        // 切换成手动需要将原来副本数量渲染到页面
        this.$set(this.formData, 'replicas', this.formDataBackUp.replicas);
      }
    },

    // 弹窗确认
    async handleConfirm() {
      this.processDialog.loading = true;
      try {
        await this.$refs.formDialog.validate(); // 校验进程名
        this.processNameActive = this.processDialog.name; // 选中当前点击tab
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


          // 需要更新外层envOverlay中副本数量
          (this.localCloudAppData.spec?.envOverlay?.replicas || []).map((e) => {
            if (e.process === this.localProcessNameActive) {
              e.process = this.processDialog.name;
            }
            return e;
          });

          this.bkappAnnotations[this.imageCrdlAnnoKey] = this.bkappAnnotations
            [this.imageLocalCrdlAnnoKey];   // 旧的bkappAnnotations数据需要赋值给新的
          delete this.bkappAnnotations[this.imageLocalCrdlAnnoKey];

        // this.handleBtnGroupClick(this.processDialog.name);
        } else {  // 新增进程
          this.panels.push({ name: this.processDialog.name });
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
            resQuotaPlan: 'default',
            envOverlay: {
              replicas: [],
            },
            autoscaling: { policy: 'default', maxReplicas: '', minReplicas: 1 },
          };
          this.localCloudAppData.spec.processes.push(this.formData);
          this.isAutoscaling = false;   // 新增进程默认为手动调节
        }
        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        this.processDialog.visiable = false;
      } catch (error) {
        console.log('error', error);
      } finally {
        this.processDialog.loading = false;
      }
    },

    // 弹窗取消
    handleDialogCancel() {
      this.processDialog.visiable = false;
      this.$refs?.formDialog.clearError();
    },

    // 页面取消
    handleCancel() {
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppDataBackUp);
      if (this.localCloudAppDataBackUp.spec) {
        this.localCloudAppData = _.cloneDeep(this.localCloudAppDataBackUp);
        this.processData = this.localCloudAppDataBackUp.spec.processes;
        this.panels = _.cloneDeep(this.processData);
      }
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
      this.isAutoscaling = !!(this.formData?.autoscaling?.minReplicas && this.formData?.autoscaling?.maxReplicas);

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

      // 手动删除镜像凭证
      delete this.localCloudAppData.metadata.annotations[this.imageCrdlAnnoKey];
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);

      this.processNameActive = 'web';
      this.btnIndex = 0;
    },

    // 过滤当前进程当前环境envOverlay中autoscaling
    handleFilterAutoscalingData(data, process) {
      if (this.isAutoscaling) {
        // 自动调节 需要过滤手动调节相关数据
        this.localCloudAppData.spec.envOverlay.replicas = (data?.replicas || [])
          .filter(e => !(e.process === process));
      } else {
        // 手动调节 需要过滤自动调节相关数据
        this.localCloudAppData.spec.envOverlay.autoscaling = (data?.autoscaling || [])
          .filter(e => !(e.process === process));
      }
    },


    // 处理资源配额相关
    handleExtraConfig() {
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
      if (!this.localCloudAppData.spec.envOverlay) {
        this.localCloudAppData.spec.envOverlay = {};
      }
      if (!this.localCloudAppData.spec.envOverlay?.resQuotas) { // 没有resQuotas时
        this.localCloudAppData.spec.envOverlay.resQuotas = [];
        this.localCloudAppData.spec.envOverlay.resQuotas.push(resQuotaPlanData);
      } else {
        this.localCloudAppData.spec.envOverlay.resQuotas
          .forEach((e) => {
            if (e.process === resQuotaPlanData.process) {
              e.envName = resQuotaPlanData.envName;
              e.plan = resQuotaPlanData.plan;
            } else {
              const resQuotasProcess = (this.localCloudAppData.spec?.envOverlay?.resQuotas || [])
                .map(e => e.process) || [];
              if (!resQuotasProcess.includes(resQuotaPlanData.process)) {   // 如果没包含就需要添加一条数据
                this.localCloudAppData.spec.envOverlay.resQuotas.push(resQuotaPlanData);
              }
            }
          });
      }


      if (this.formData.replicas) {     // 副本数量
        console.log('this.localCloudAppData.spec 处理资源', this.localCloudAppData.spec.envOverlay?.replicas);
        // 没有replicas时
        if (!this.localCloudAppData.spec.envOverlay?.replicas
        || !this.localCloudAppData.spec.envOverlay.replicas.length) {
          this.localCloudAppData.spec.envOverlay.replicas = [];
          this.localCloudAppData.spec.envOverlay.replicas.push(replicasData);
          console.log('replicas', this.localCloudAppData.spec.envOverlay.replicas);
        } else {
          // 有replicas数据
          this.localCloudAppData.spec.envOverlay.replicas.forEach((e) => {
            if (e.process === replicasData.process) {
              e.envName = replicasData.envName;
              e.count = replicasData.count;
            } else {
              const replicasProcess = (this.localCloudAppData.spec?.envOverlay?.replicas || []).map(e => e.process);
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
        const autoscalingData = {
          envName: this.envName,
          process: this.processNameActive,
          policy: 'default',
          minReplicas: this.formData.autoscaling.minReplicas ? Number(this.formData.autoscaling.minReplicas) : 1,
          maxReplicas: this.formData.autoscaling.maxReplicas ? Number(this.formData.autoscaling.maxReplicas) : '',
        };
        // 没有autoscaling时
        if (!this.localCloudAppData.spec.envOverlay?.autoscaling?.length) {
          this.localCloudAppData.spec.envOverlay.autoscaling = [];
          this.localCloudAppData.spec.envOverlay.autoscaling.push(autoscalingData);
        } else {
          // 有autoscaling数据
          this.localCloudAppData.spec.envOverlay.autoscaling
            .forEach((e) => {
              if (e.process === autoscalingData.process) {
                e.envName = autoscalingData.envName;
                e.minReplicas =  autoscalingData.minReplicas;
                e.maxReplicas = autoscalingData.maxReplicas;
              } else {
                const autoscalingProcess = (this.localCloudAppData.spec?.envOverlay?.autoscaling || [])
                  .map(e => e.process) || [];
                if (!autoscalingProcess.includes(autoscalingData.process)) {   // 如果没包含就需要添加一条数据
                  this.localCloudAppData.spec.envOverlay.autoscaling.push(autoscalingData);
                }
              }
            });
        }

        // replicas做一次备份
        if (this.localCloudAppData.spec.processes[this.btnIndex].replicas) {
          this.formDataBackUp.replicas = this.localCloudAppData.spec.processes[this.btnIndex].replicas;
        }
        // 需要删除手动调节相关信息
        delete this.localCloudAppData.spec.processes[this.btnIndex].replicas;
        // 过滤当前进程当前环境envOverlay中replicas
        const { envOverlay } = this.localCloudAppData.spec;
        this.handleFilterAutoscalingData(envOverlay, this.processNameActive);  // 传入envOverlay、当前进程名
      } else { // // 手动调节
        // autoscaling做一次备份
        if (this.localCloudAppData.spec.processes[this.btnIndex].autoscaling) {
          this.formDataBackUp.autoscaling = this.localCloudAppData.spec.processes[this.btnIndex].autoscaling;
        }
        // 需要删除当前进程base中的autoscaling
        delete this.localCloudAppData.spec.processes[this.btnIndex].autoscaling;
        // 过滤当前进程当前环境envOverlay中autoscaling
        const { envOverlay } = this.localCloudAppData.spec;
        // eslint-disable-next-line max-len
        this.handleFilterAutoscalingData(envOverlay, this.processNameActive);  // 传入envOverlay、当前进程名
      }

      // 将最大值最小值改为数字类型
      (this.localCloudAppData.spec?.processes || []).forEach((e) => {
        if (e.autoscaling) {
          e.autoscaling.minReplicas = e.autoscaling.minReplicas ? Number(e.autoscaling.minReplicas) : '';
          e.autoscaling.maxReplicas = e.autoscaling.maxReplicas ? Number(e.autoscaling.maxReplicas) : '';
        }
      });
    },

    // 镜像选择
    handleImageChange(val) {
      console.log(val, this.bkappAnnotations);
      if (this.bkappAnnotations[this.imageCrdlAnnoKey]) {
        this.$set(this.localCloudAppData.metadata, 'annotations', this.bkappAnnotations);
        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
      }
    },

    async getQuotaPlans() {
      try {
        this.quotaPlansFlag = true;
        const res =  await this.$store.dispatch('deploy/fetchQuotaPlans', {});
        const data = res.find(e => e.name === (this.formData.resQuotaPlan || 'default'));
        this.limit = data.limit;
        this.request = data.request;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.quotaPlansFlag = false;
      }
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
        margin: 10px 40px 20px;
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
        max-width: calc(100% - 85px);
        flex-flow: wrap;
         .item-close-icon{
            position: absolute;
            top: 4px;
            right: 0px;
            font-size: 22px;
            width: 22px;
            height: 22px;
            line-height: 22px;
            cursor: pointer;
        }
      }
    }
    .form-detail{
      .form-text{
        color: #313238;
        padding-left: 10px;
      }
    }
    .env-name{
      color: #313238;
      font-size: 14px;
    }
    .env-container{
      width: 885px;
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
        right: 540px !important;
        top: 7px !important;
      }
    }
</style>
