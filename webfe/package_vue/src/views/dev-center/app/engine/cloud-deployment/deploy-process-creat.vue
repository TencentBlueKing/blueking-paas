<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-process-loading"
    :offset-top="0"
    :is-transition="false"
    :offset-left="20"
    class="deploy-action-box"
  >
    <!-- 若托管方式为源码&镜像，进程配置页面都为当前空页面状态 -->
    <section
      v-if="!isCustomImage && !isCreate"
      style="margin-top: 38px;"
    >
      <bk-exception
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        <p
          class="mt10"
          style="color: #979BA5;font-size: 12px;"
        >
          {{ $t('进程名和启动命令在构建目录下的 app_desc.yaml 文件中定义。') }}
        </p>
        <p class="guide-link mt15" @click="handleViewGuide">{{ $t('查看使用指南') }}</p>
      </bk-exception>
    </section>
    <div
      v-else
      class="process-container"
    >
      <div
        class="btn-container flex-row align-items-baseline"
        :class="[isPageEdit ? '' : 'justify-content-between']"
      >
        <div class="bk-button-group bk-button-group-cls">
          <bk-button
            v-for="(panel, index) in panels"
            :key="index"
            :class="[processNameActive === panel.name ? 'is-selected' : '', 'mb10']"
            @click="handleBtnGroupClick(panel.name, index)"
          >
            {{ panel.name }}
            <i
              v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
              class="paasng-icon paasng-edit-2 pl5 pr10"
              ref="tooltipsHtml"
              @click="handleProcessNameEdit(panel.name, index)"
              v-bk-tooltips="$t('编辑')"
            />

            <bk-popconfirm
              :content="$t('确认删除该进程')"
              width="288"
              style="display: inline-block"
              class="item-close-icon"
              trigger="click"
              @confirm="handleDelete(panel.name, index)"
            >
              <i
                v-if="processNameActive === panel.name && index !== 0 && isPageEdit"
                class="paasng-icon paasng-icon-close"
                v-bk-tooltips="$t('删除')"
              />
            </bk-popconfirm>
          </bk-button>
        </div>
        <span
          v-if="isPageEdit"
          class="pl10"
        >
          <bk-button
            text
            theme="primary"
            @click="handleProcessNameEdit('')"
          >
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
          @click="handleEditClick"
        >
          {{ $t('编辑') }}
        </bk-button>
      </div>
      <div
        class="form-deploy"
        v-if="isPageEdit"
      >
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
            <!-- v1alpha2 镜像仓库不带tag -->
            <bk-form-item
              :label="$t('镜像仓库')"
              :label-width="120"
              v-if="isV1alpha2"
            >
              {{ buildData.image }}
              <i
                v-if="!isCreate"
                class="paasng-icon paasng-edit-2 image-store-icon"
                @click="handleToModuleInfo"
              />
            </bk-form-item>
            <!-- v1alpha1 镜像地址 -->
            <bk-form-item
              :label="$t('镜像地址')"
              :required="true"
              :label-width="120"
              :property="'image'"
              :rules="rules.image"
              v-else-if="isCustomImage && !isV1alpha2"
            >
              <bk-input
                ref="mirrorUrl"
                v-model="formData.image"
                style="width: 500px"
                :placeholder="$t('请输入带标签的镜像仓库')"
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
                >
                  {{ $t('使用示例镜像') }}
                </span>
              </p>
              <p :class="['whole-item-tips', localLanguage === 'en' ? '' : 'no-wrap']">
                <span>{{ $t('镜像应监听“容器端口”处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>&nbsp;
                <a
                  target="_blank"
                  :href="GLOBAL.DOC.BUILDING_MIRRIRS_DOC"
                >
                  {{ $t('帮助：如何构建镜像') }}
                </a>
              </p>
            </bk-form-item>

            <bk-form-item
              :label="$t('镜像凭证')"
              :label-width="120"
              v-if="isV1alpha2"
            >
              {{ buildData.imageCredentialsName || '--' }}
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
                style="width: 500px"
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
                  style="cursor: pointer"
                  @click="handlerCreateImageCredential"
                >
                  <i class="bk-icon icon-plus-circle mr5" />
                  {{ $t('新建凭证') }}
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
                :key="tagInputIndex"
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
                style="right: 8px"
              />
              <p class="whole-item-tips">
                {{ $t('接收 HTTP 请求的端口号．建议镜像直接监听 $PORT 环境变量不修改本值') }}
              </p>
            </bk-form-item>
            <bk-form-item :label-width="40">
              <bk-button
                text
                theme="primary"
                :title="$t('更多配置')"
                @click="ifopen = !ifopen"
              >
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
              <!-- <bk-radio-group v-model="envName">
                <bk-radio-button
                  class="radio-cls"
                  v-for="(item, index) in envsData"
                  :key="index"
                  :value="item.value">
                  {{ item.label }}
                </bk-radio-button>
              </bk-radio-group> -->
            </bk-form-item>
            <bk-form-item
              v-show="ifopen"
              :label-width="40"
            >
              <div class="env-name w885">{{ $t('预发布环境') }}</div>
              <div class="env-container">
                <bk-form
                  ref="formStagEnv"
                  :model="extraConfigData.stag"
                  ext-cls="form-envs"
                >
                  <bk-form-item
                    :label="$t('资源配额方案')"
                    :label-width="120"
                  >
                    <div class="flex-row align-items-center">
                      <bk-select
                        v-model="extraConfigData.stag.resQuotaPlan.plan"
                        :disabled="false"
                        style="width: 150px"
                        searchable
                        @change="handleChange($event, 'stag')"
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
                      <quota-popver v-else :data="stagQuotaData" />
                    </div>
                  </bk-form-item>
                  <bk-form-item
                    :label="$t('扩缩容方式')"
                    :label-width="120"
                  >
                    <section :class="{ 'flex-row': localLanguage !== 'en' }">
                      <bk-radio-group
                        v-model="extraConfigData.stag.isAutoscaling"
                        @change="handleRadioChange('stag')"
                        style="flex: 1"
                      >
                        <bk-radio-button
                          class="radio-cls"
                          :value="false"
                        >
                          {{ $t('手动调节') }}
                        </bk-radio-button>
                        <!-- 创建应用、模块禁用自动调节 -->
                        <bk-radio-button
                          class="radio-cls"
                          :value="true"
                          :disabled="isCreate"
                          v-bk-tooltips="{
                            content: $t('请创建成功后，到“模块配置”页面开启自动调节扩缩容。'),
                          }"
                        >
                          {{ $t('自动调节') }}
                        </bk-radio-button>
                      </bk-radio-group>

                      <bk-alert
                        v-if="extraConfigData.stag.isAutoscaling"
                        type="info"
                        :class="{ mt10: localLanguage === 'en' }"
                        style="margin-right: 60px"
                      >
                        <span slot="title">
                          {{ $t('根据当前负载和触发条件中设置的阈值自动扩缩容') }}
                          <a
                            target="_blank"
                            :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/paas3_autoscaling'"
                            style="color: #3a84ff"
                          >
                            {{ $t('查看动态扩缩容计算规则') }}
                          </a>
                        </span>
                      </bk-alert>
                    </section>
                  </bk-form-item>
                  <bk-form-item
                    v-if="extraConfigData.stag.isAutoscaling"
                    :label="$t('触发方式')"
                    :label-width="120"
                    class="desc-form-item"
                  >
                    <div class="desc-container flex-row">
                      <bk-select
                        v-model="cpuLabel"
                        disabled
                        style="width: 150px"
                      >
                        <bk-option
                          v-for="option in triggerMethodData"
                          :id="option"
                          :key="option"
                          :name="option"
                        />
                      </bk-select>
                      <div class="mr10 ml10">=</div>
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
                  <section
                    v-if="extraConfigData.stag.isAutoscaling"
                    class="mt20"
                  >
                    <bk-form-item
                      :label="$t('最小副本数')"
                      :label-width="120"
                      :required="true"
                      :property="'formAutoscalingData.minReplicas'"
                      :rules="rules.stagMinReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.stag.formAutoscalingData.minReplicas"
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
                      :property="'formAutoscalingData.maxReplicas'"
                      :rules="rules.stagMaxReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.stag.formAutoscalingData.maxReplicas"
                        type="number"
                        :max="5"
                        :min="1"
                        style="width: 150px"
                      />
                    </bk-form-item>
                  </section>
                  <section
                    v-else
                    class="mt20"
                  >
                    <bk-form-item
                      :label="$t('副本数量')"
                      :label-width="120"
                      :required="true"
                      :property="'formReplicas'"
                      :rules="rules.formReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.stag.formReplicas"
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
            <bk-form-item
              v-show="ifopen"
              :label-width="40"
            >
              <div class="env-name w885">{{ $t('生产环境') }}</div>
              <div class="env-container">
                <bk-form
                  ref="formProdEnv"
                  :model="extraConfigData.prod"
                  ext-cls="form-envs"
                >
                  <bk-form-item
                    :label="$t('资源配额方案')"
                    :label-width="120"
                  >
                    <div class="flex-row align-items-center">
                      <bk-select
                        v-model="extraConfigData.prod.resQuotaPlan.plan"
                        :disabled="false"
                        style="width: 150px"
                        searchable
                        @change="handleChange($event, 'prod')"
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
                      <quota-popver v-else :data="prodQuotaData" />
                    </div>
                  </bk-form-item>
                  <bk-form-item
                    :label="$t('扩缩容方式')"
                    :label-width="120"
                  >
                    <section :class="{ 'flex-row': localLanguage !== 'en' }">
                      <bk-radio-group
                        v-model="extraConfigData.prod.isAutoscaling"
                        @change="handleRadioChange('prod')"
                        style="flex: 1"
                      >
                        <bk-radio-button
                          class="radio-cls"
                          :value="false"
                        >
                          {{ $t('手动调节') }}
                        </bk-radio-button>
                        <!-- 创建应用、模块禁用自动调节 -->
                        <bk-radio-button
                          class="radio-cls"
                          :value="true"
                          :disabled="isCreate"
                          v-bk-tooltips="{
                            content: $t('请创建成功后，到“模块配置”页面开启自动调节扩缩容。'),
                          }"
                        >
                          {{ $t('自动调节') }}
                        </bk-radio-button>
                      </bk-radio-group>

                      <bk-alert
                        v-if="extraConfigData.prod.isAutoscaling"
                        type="info"
                        :class="{ mt10: localLanguage === 'en' }"
                        style="margin-right: 60px"
                      >
                        <span slot="title">
                          {{ $t('根据当前负载和触发条件中设置的阈值自动扩缩容') }}
                          <a
                            target="_blank"
                            :href="GLOBAL.LINK.BK_APP_DOC + 'topics/paas/paas3_autoscaling'"
                            style="color: #3a84ff"
                          >
                            {{ $t('查看动态扩缩容计算规则') }}
                          </a>
                        </span>
                      </bk-alert>
                    </section>
                  </bk-form-item>
                  <bk-form-item
                    v-if="extraConfigData.prod.isAutoscaling"
                    :label="$t('触发方式')"
                    :label-width="120"
                    class="desc-form-item"
                  >
                    <div class="desc-container flex-row">
                      <bk-select
                        v-model="cpuLabel"
                        disabled
                        style="width: 150px"
                      >
                        <bk-option
                          v-for="option in triggerMethodData"
                          :id="option"
                          :key="option"
                          :name="option"
                        />
                      </bk-select>
                      <div class="mr10 ml10">=</div>
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
                  <section
                    v-if="extraConfigData.prod.isAutoscaling"
                    class="mt20"
                  >
                    <bk-form-item
                      :label="$t('最小副本数')"
                      :label-width="120"
                      :required="true"
                      :property="'formAutoscalingData.maxReplicas'"
                      :rules="rules.prodMinReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.prod.formAutoscalingData.minReplicas"
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
                      :property="'formAutoscalingData.maxReplicas'"
                      :rules="rules.prodMaxReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.prod.formAutoscalingData.maxReplicas"
                        type="number"
                        :max="5"
                        :min="1"
                        style="width: 150px"
                      />
                    </bk-form-item>
                  </section>
                  <section
                    v-else
                    class="mt20"
                  >
                    <bk-form-item
                      :label="$t('副本数量')"
                      :label-width="120"
                      :required="true"
                      :property="'formReplicas'"
                      :rules="rules.formReplicas"
                    >
                      <bk-input
                        v-model="extraConfigData.prod.formReplicas"
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
      <div
        class="form-detail mt20"
        v-else
      >
        <bk-form :model="formData">
          <!-- v1alpha1 是镜像地址，v1alpha2是镜像仓库不带tag -->
          <bk-form-item
            v-if="isV1alpha2"
            :label="`${$t('镜像仓库')}：`"
          >
            <span class="form-text">{{ buildData.image || '--' }}</span>
          </bk-form-item>
          <bk-form-item
            v-else-if="isCustomImage && !isV1alpha2"
            :label="`${$t('镜像地址')}：`"
          >
            <span class="form-text">{{ formData.image || '--' }}</span>
          </bk-form-item>
          <bk-form-item :label="`${$t('镜像凭证')}：`">
            <span class="form-text">
              {{ isV1alpha2 ? buildData.imageCredentialsName : bkappAnnotations[imageCrdlAnnoKey] || '--' }}
            </span>
          </bk-form-item>
          <bk-form-item :label="`${$t('启动命令')}：`">
            <span v-if="formData.command.length">
              <bk-tag
                v-for="item in formData.command"
                :key="item"
              >
                {{ item }}
              </bk-tag>
            </span>
            <span
              class="form-text"
              v-else
            >
              --
            </span>
          </bk-form-item>
          <bk-form-item :label="`${$t('命令参数')}：`">
            <span v-if="formData.args.length">
              <bk-tag
                v-for="item in formData.args"
                :key="item"
              >
                {{ item }}
              </bk-tag>
            </span>
            <span
              class="form-text"
              v-else
            >
              --
            </span>
          </bk-form-item>
          <bk-form-item :label="`${$t('容器端口')}：`">
            <span class="form-text">{{ formData.targetPort || '--' }}</span>
          </bk-form-item>
          <bk-form-item :label-width="50">
            <bk-button
              text
              theme="primary"
              :title="$t('更多配置')"
              @click="ifopen = !ifopen"
            >
              {{ $t('更多配置') }}
              <i
                class="paasng-icon"
                :class="ifopen ? 'paasng-angle-double-up' : 'paasng-angle-double-down'"
              />
            </bk-button>
          </bk-form-item>
          <section
            class="mt20 extra-config-cls"
            v-if="ifopen"
          >
            <bk-form-item :label="`${$t('配置环境')}：`">
              <!-- <span class="form-text">{{ ENV_ENUM[envName] || '--' }}</span> -->
              <div class="flex-row env-detail">
                <div
                  v-for="item in envsData"
                  :key="item.value"
                  :class="item.value === 'prod' ? 'ml20' : ''"
                >
                  <div class="env-name">{{ item.label }}</div>
                  <div class="env-item">
                    <bk-form-item
                      :label="`${$t('资源配额方案')}：`"
                      ext-cls="form-first-cls"
                    >
                      <span class="form-text">{{ extraConfigData[item.value].resQuotaPlan.plan || '--' }}</span>
                      <span slot="tip">
                        <i
                          v-if="quotaPlansFlag"
                          class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                        />
                        <quota-popver v-else :data="item.value === 'stag' ? stagQuotaData : prodQuotaData" />
                      </span>
                    </bk-form-item>

                    <bk-form-item :label="`${$t('扩缩容方式')}：`">
                      <span class="form-text">
                        {{ extraConfigData[item.value].isAutoscaling ? $t('自动调节') : $t('手动调节') }}
                      </span>
                    </bk-form-item>

                    <section v-if="extraConfigData[item.value].isAutoscaling">
                      <bk-form-item :label="`${$t('最小副本数')}：`">
                        <span class="form-text">
                          {{ extraConfigData[item.value].formAutoscalingData.minReplicas || '--' }}
                        </span>
                      </bk-form-item>
                      <bk-form-item :label="`${$t('最大副本数')}：`">
                        <span class="form-text">
                          {{ extraConfigData[item.value].formAutoscalingData.maxReplicas || '--' }}
                        </span>
                      </bk-form-item>
                    </section>
                    <section v-else>
                      <bk-form-item :label="$t('副本数量：')">
                        <span class="form-text">{{ extraConfigData[item.value].formReplicas || '--' }}</span>
                      </bk-form-item>
                    </section>
                  </div>
                </div>
              </div>
            </bk-form-item>
          </section>
        </bk-form>
      </div>

      <!-- 创建应用于与模块需隐藏 -->
      <div
        class="process-btn-wrapper"
        v-if="isPageEdit && isComponentBtn"
      >
        <bk-button
          class="pl20 pr20"
          :theme="'primary'"
          @click="$emit('save')"
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
        :label-width="0"
      >
        <bk-form-item
          :required="true"
          :property="'name'"
          :rules="rules.processName"
        >
          <bk-input
            class="path-input-cls"
            v-model="processDialog.name"
            :placeholder="$t('请输入进程名称')"
            @enter="handleConfirm"
          ></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 指南 -->
    <user-guide name="process" ref="userGuideRef" />
  </paas-content-loader>
</template>

<script>import _ from 'lodash';
import { bus } from '@/common/bus';
import { RESQUOTADATA, ENV_ENUM } from '@/common/constants';
import userGuide from './comps/user-guide/index.vue';
import quotaPopver from './comps/quota-popver';

export default {
  components: {
    userGuide,
    quotaPopver,
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
    isCreate: {
      type: Boolean,
      default: false,
    },
    // 组件内部按钮操作
    isComponentBtn: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      panels: [],
      processNameActive: 'web', // 选中的进程名
      btnIndex: 0,
      panelActive: 0,
      formData: {
        image: '',
        name: 'web',
        command: [],
        args: [],
        memory: '256Mi',
        cpu: '500m',
        targetPort: 5000,
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
            regex: /^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*\/)*[a-z0-9]+(?:[._-][a-z0-9]+)*:[a-zA-Z0-9_]+$/,
            message: this.$t('请输入包含标签(tag)的镜像地址'),
            trigger: 'blur',
          },
        ],
        formReplicas: [
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
        stagMinReplicas: [
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
              const maxReplicas = Number(this.extraConfigData.stag.formAutoscalingData.maxReplicas);
              return minReplicas <= maxReplicas;
            },
            message: () => `${this.$t('最小副本数不可大于最大副本数')}`,
            trigger: 'blur',
          },
        ],
        stagMaxReplicas: [
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
              const minReplicas = Number(this.extraConfigData.stag.formAutoscalingData.minReplicas);
              return maxReplicas >= minReplicas;
            },
            message: `${this.$t('最大副本数不可小于最小副本数')}`,
            trigger: 'blur',
          },
        ],
        prodMinReplicas: [
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
              const maxReplicas = Number(this.extraConfigData.prod.formAutoscalingData.maxReplicas);
              return minReplicas <= maxReplicas;
            },
            message: () => `${this.$t('最小副本数不可大于最大副本数')}`,
            trigger: 'blur',
          },
        ],
        prodMaxReplicas: [
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
              const minReplicas = Number(this.extraConfigData.prod.formAutoscalingData.minReplicas);
              return maxReplicas >= minReplicas;
            },
            message: `${this.$t('最大副本数不可小于最小副本数')}`,
            trigger: 'blur',
          },
        ],
        processName: [
          {
            required: true,
            message: this.$t('请输入进程名称'),
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
      imageCredential: '',
      imageCredentialList: [],
      targetPortErrTips: '',
      isTargetPortErrTips: false,
      ifopen: false,
      envsData: [
        { value: 'stag', label: this.$t('预发布环境') },
        { value: 'prod', label: this.$t('生产环境') },
      ],
      resQuotaData: RESQUOTADATA,
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
      quotaPlansFlag: false,
      triggerMethodData: ['CPU 使用率'],
      cpuLabel: 'CPU 使用率',
      cpuValue: '85%',
      extraConfigData: {
        stag: {
          resQuotaPlan: {},
          isAutoscaling: false,
          formAutoscalingData: { minReplicas: '', maxReplicas: '', policy: 'default' },
          formReplicas: 1,
          limit: {},
          request: {},
        },
        prod: {
          resQuotaPlan: {},
          isAutoscaling: false,
          formAutoscalingData: { minReplicas: '', maxReplicas: '', policy: 'default' },
          formReplicas: 1,
          limit: {},
          request: {},
        },
      },
      tagInputIndex: 0,
      allQuotaList: [],
      stagQuotaData: {},
      prodQuotaData: {},
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
      if (this.isV1alpha2) return '';
      return `bkapp.paas.bk.tencent.com/image-credentials.${this.processNameActive}`;
    },
    imageLocalCrdlAnnoKey() {
      return `bkapp.paas.bk.tencent.com/image-credentials.${this.localProcessNameActive}`;
    },
    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit || this.$store.state.cloudApi.processPageEdit;
    },
    isV1alpha2() {
      return this.localCloudAppData?.apiVersion?.includes('v1alpha2');
    },
    curModuleId() {
      return this.curAppModule?.name;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    isCustomImage() {
      return this.curAppModule?.web_config?.runtime_type === 'custom_image';
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
          this.bkappAnnotations = this.localCloudAppData.metadata.annotations;
          if (this.isCreate) {
            // 使用示例镜像，启动命令默认值
            if (this.buildData.image === 'mirrors.tencent.com/bkpaas/django-helloworld') {
              this.formData.command = ['bash', '/app/start_web.sh'];
            } else {
              this.formData.command = [];
              this.formData.targetPort = '';
            }
          }
        }
        this.panels = _.cloneDeep(this.processData);
      },
      immediate: true,
    },
    formData: {
      handler(val) {
        this.envOverlayData = this.localCloudAppData?.spec?.envOverlay || {};
        if (this.localCloudAppData.spec) {
          val.name = this.processNameActive;
          if (val.targetPort && /^\d+$/.test(val.targetPort)) { // 有值且为数字字符串
            val.targetPort = Number(val.targetPort);
          }

          // 更多配置信息
          // 资源配额方案
          this.extraConfigData.stag.resQuotaPlan = (this.envOverlayData?.resQuotas || []).find(e => e.process === this.processNameActive && e.envName === 'stag') || { plan: 'default' };
          this.extraConfigData.prod.resQuotaPlan = (this.envOverlayData?.resQuotas || []).find(e => e.process === this.processNameActive && e.envName === 'prod') || { plan: 'default' };

          // 扩缩容-自动
          const autoscalingStag = (this.envOverlayData?.autoscaling || []).find(e => e.process === this.processNameActive && e.envName === 'stag');
          const autoscalingProd = (this.envOverlayData?.autoscaling || []).find(e => e.process === this.processNameActive && e.envName === 'prod');
          this.extraConfigData.stag.isAutoscaling = !!autoscalingStag;
          this.extraConfigData.prod.isAutoscaling = !!autoscalingProd;

          // 扩缩容-手动
          const replicasStag = (this.envOverlayData?.replicas || []).find(e => e.process === this.processNameActive && e.envName === 'stag') || { count: 1 };
          const replicasProd = (this.envOverlayData?.replicas || []).find(e => e.process === this.processNameActive && e.envName === 'prod') || { count: 1 };

          // 自动
          if (!!autoscalingStag) {
            this.extraConfigData.stag.formAutoscalingData.maxReplicas = autoscalingStag.maxReplicas;
            this.extraConfigData.stag.formAutoscalingData.minReplicas = autoscalingStag.minReplicas;
          } else { // 手动
            this.extraConfigData.stag.formReplicas = replicasStag.count;
          }

          if (!!autoscalingProd) {
            this.extraConfigData.prod.formAutoscalingData.maxReplicas = autoscalingProd.maxReplicas;
            this.extraConfigData.prod.formAutoscalingData.minReplicas = autoscalingProd.minReplicas;
          } else {
            this.extraConfigData.prod.formReplicas = replicasProd.count;
          }

          this.$set(this.localCloudAppData.spec.processes, this.btnIndex, val); // 赋值数据给选中的进程

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

    'extraConfigData.stag': {
      handler(val) {
        this.envName = 'stag';
        if (Object.keys(this.localCloudAppData).length) {
          this.handleExtraConfig(); // 处理额外的配置
        }

        // 扩缩容
        if (val?.formAutoscalingData?.maxReplicas >= val?.formAutoscalingData?.minReplicas) {
          this.$refs.formStagEnv?.clearError();
        }

        if (val?.formAutoscalingData?.minReplicas <= val?.formAutoscalingData?.maxReplicas) {
          this.$refs.formStagEnv?.clearError();
        }
      },
      deep: true,
    },
    'extraConfigData.prod': {
      handler(val) {
        this.envName = 'prod';
        if (Object.keys(this.localCloudAppData).length) {
          this.handleExtraConfig(); // 处理额外的配置
        }

        // 扩缩容
        if (val?.formAutoscalingData?.maxReplicas >= val?.formAutoscalingData?.minReplicas) {
          this.$refs.formProdEnv?.clearError();
        }

        if (val?.formAutoscalingData?.minReplicas <= val?.formAutoscalingData?.maxReplicas) {
          this.$refs.formProdEnv?.clearError();
        }
      },
      deep: true,
    },

    'extraConfigData.stag.resQuotaPlan.plan'() {
      this.getQuotaPlans('stag');
    },

    'extraConfigData.prod.resQuotaPlan.plan'() {
      this.getQuotaPlans('prod');
    },

    panels: {
      handler(val) {
        if (!val.length) return;
        const isDisabled = val[this.panelActive].isEdit;
        bus.$emit('release-disabled', isDisabled);
      },
      deep: true,
    },

    isV1alpha2(val) {
      // v2每个进程不需要 image、imagePullPolicy
      if (val) {
        this.localCloudAppData?.spec?.processes.forEach((e) => {
          delete e.image;
          delete e.imagePullPolicy;
        });
        setTimeout(() => {
          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        }, 500);
      } else {
        this.getImageCredentialList();
      }
    },
  },
  async created() {
    // 非创建应用初始化为查看态
    if (!this.isCreate) {
      this.$store.commit('cloudApi/updateProcessPageEdit', false);
      this.$store.commit('cloudApi/updatePageEdit', false);
    }
    this.getQuotaPlans();
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
      this.localProcessNameActive = v; // 点击的tab名，编辑数据时需要用到
      this.processNameActive = v;
      this.btnIndex = i;
      // tag-input 输入切换问题
      this.tagInputIndex++;
    },

    // 编辑
    handleEditClick() {
      if (this.isCreate) {
        this.$store.commit('cloudApi/updateProcessPageEdit', true);
      } else {
        this.$store.commit('cloudApi/updatePageEdit', true);
      }
    },

    // 处理保存时数据问题
    async handleProcessData() {
      try {
        await this.$refs?.formStagEnv?.validate();
        await this.$refs?.formProdEnv?.validate();
        await this.$refs?.formDeploy?.validate();
        return true;
      } catch (error) {
        console.log('error', error);
        return false;
      }
    },

    // 处理自动调节问题
    handleRadioChange(env) {
      if (env === 'stag') {
        this.$refs.formStagEnv?.clearError();
      } else {
        this.$refs.formStagEnv?.clearError();
      }
    },

    // 弹窗确认
    async handleConfirm() {
      this.processDialog.loading = true;
      try {
        await this.$refs.formDialog.validate(); // 校验进程名
        this.processNameActive = this.processDialog.name; // 选中当前点击tab
        if (this.processDialog.index) { // 编辑进程名
          this.panels.forEach((e, i) => {
            if (i === this.processDialog.index) {
              e.name = this.processDialog.name;
            }
          });
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

          this.bkappAnnotations[this.imageCrdlAnnoKey] = this.bkappAnnotations[this.imageLocalCrdlAnnoKey]; // 旧的bkappAnnotations数据需要赋值给新的
          delete this.bkappAnnotations[this.imageLocalCrdlAnnoKey];

          // this.handleBtnGroupClick(this.processDialog.name);
        } else {
          // 新增进程
          this.panels.push({ name: this.processDialog.name });
          this.btnIndex = this.panels.length - 1;
          this.formData = {
            name: this.processDialog.name,
            image: '',
            command: [],
            args: [],
            memory: '256Mi',
            cpu: '500m',
            targetPort: null,
          };
          if (this.isV1alpha2) {
            delete this.formData.image; // v2不需要image
          }
          this.localCloudAppData.spec.processes.push(this.formData);
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
      this.$refs?.formDialog?.clearError();
    },

    // 页面取消
    handleCancel() {
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppDataBackUp);
      if (this.localCloudAppDataBackUp.spec) {
        this.localCloudAppData = _.cloneDeep(this.localCloudAppDataBackUp);
        this.processData = this.localCloudAppDataBackUp.spec.processes;
        this.panels = _.cloneDeep(this.processData);
        this.formData = _.cloneDeep(this.processData[this.btnIndex]);
      }
    },

    // 编辑进程名称
    handleProcessNameEdit(processName, i = '') {
      this.processDialog.visiable = true;
      this.processDialog.name = processName;
      this.processDialog.index = i; // 如果为空 这代表是新增
    },

    // 删除某个进程
    handleDelete(processName, i = '') {
      this.localCloudAppData.spec.processes.splice(i, 1);
      // eslint-disable-next-line prefer-destructuring
      this.formData = this.processData[0];

      // 过滤外层envOverlay中的自动调节数据
      this.localCloudAppData.spec.envOverlay.autoscaling = (this.localCloudAppData.spec.envOverlay.autoscaling || []).filter(e => e.process !== this.processNameActive);

      // 过滤外层envOverlay中配额数据
      this.localCloudAppData.spec.envOverlay.resQuotas = (this.localCloudAppData.spec.envOverlay.resQuotas || []).filter(e => e.process !== this.processNameActive);

      // 过滤外层envOverlay中副本数量
      this.localCloudAppData.spec.envOverlay.replicas = (this.localCloudAppData.spec.envOverlay?.replicas || []).filter(e => e.process !== this.processNameActive);

      this.processData = this.localCloudAppData.spec.processes;
      this.panels = _.cloneDeep(this.processData);

      // // 手动删除镜像凭证
      // delete this.localCloudAppData.metadata.annotations[this.imageCrdlAnnoKey];
      // this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);

      this.processNameActive = 'web';
      this.btnIndex = 0;
    },

    // 过滤当前进程当前环境envOverlay中autoscaling
    handleFilterAutoscalingData(data, process) {
      if (this.extraConfigData[this.envName].isAutoscaling) {
        // 自动调节 需要过滤手动调节相关数据
        this.localCloudAppData.spec.envOverlay.replicas = (data?.replicas || []).filter(e => !(e.process === process && e.envName === this.envName));
      } else {
        // 手动调节 需要过滤自动调节相关数据
        this.localCloudAppData.spec.envOverlay.autoscaling = (data?.autoscaling || []).filter(e => !(e.process === process && e.envName === this.envName));
      }
    },

    // 处理资源配额相关
    handleExtraConfig() {
      // 副本数量相关数据
      const replicasData = {
        envName: this.envName,
        process: this.processNameActive,
        count: this.extraConfigData[this.envName].formReplicas,
      };
      // // 资源配置相关数据
      const resQuotaPlanData = {
        envName: this.envName,
        process: this.processNameActive,
        plan: this.extraConfigData[this.envName].resQuotaPlan.plan,
      };
      if (!this.localCloudAppData?.spec?.envOverlay) {
        this.localCloudAppData.spec.envOverlay = {};
      }

      const resQuotasWithProcessEnv = (this.localCloudAppData.spec?.envOverlay?.resQuotas || []).filter(e => e.process === resQuotaPlanData.process && e.envName === resQuotaPlanData.envName) || [];

      const resQuotasFilterData = (this.localCloudAppData.spec?.envOverlay?.resQuotas || []).filter(e => e.process !== resQuotaPlanData.process || e.envName !== resQuotaPlanData.envName) || [];

      if (!resQuotasWithProcessEnv.length) {
        // 没有resQuotas时
        if (!this.localCloudAppData.spec.envOverlay.resQuotas) {
          this.localCloudAppData.spec.envOverlay.resQuotas = [];
        }
        this.localCloudAppData.spec.envOverlay.resQuotas.push(resQuotaPlanData);
      } else {
        resQuotasWithProcessEnv.forEach((e) => {
          if (e.process === resQuotaPlanData.process && e.envName === resQuotaPlanData.envName) {
            e.plan = resQuotaPlanData.plan;
          }
        });
        this.localCloudAppData.spec.envOverlay.resQuotas = [...resQuotasFilterData, ...resQuotasWithProcessEnv];
      }

      if (replicasData.count) {
        // 副本数量
        const replicasWithProcessEnv = (this.localCloudAppData.spec?.envOverlay?.replicas || []).filter(e => e.process === replicasData.process && e.envName === replicasData.envName) || [];

        const replicasFilterData = (this.localCloudAppData.spec?.envOverlay?.replicas || []).filter(e => e.process !== replicasData.process || e.envName !== replicasData.envName) || [];
        if (!replicasWithProcessEnv.length) {
          if (!this.localCloudAppData.spec.envOverlay.replicas) {
            this.localCloudAppData.spec.envOverlay.replicas = [];
          }
          this.localCloudAppData.spec.envOverlay.replicas.push(replicasData);
        } else {
          replicasWithProcessEnv.forEach((e) => {
            if (e.process === replicasData.process && e.envName === replicasData.envName) {
              e.count = replicasData.count;
            }
          });
          this.localCloudAppData.spec.envOverlay.replicas = [...replicasFilterData, ...replicasWithProcessEnv];
        }
      }

      // 自动调节
      if (this.extraConfigData[this.envName].isAutoscaling) {
        const { minReplicas } = this.extraConfigData[this.envName].formAutoscalingData;
        const { maxReplicas } = this.extraConfigData[this.envName].formAutoscalingData;
        // 自动调节相关数据
        const autoscalingData = {
          envName: this.envName,
          process: this.processNameActive,
          policy: 'default',
          minReplicas: minReplicas ? Number(minReplicas) : 1,
          maxReplicas: maxReplicas ? Number(maxReplicas) : '',
        };
        const autoscalingWithProcessEnv =          (this.localCloudAppData.spec?.envOverlay?.autoscaling || []).filter(e => e.process === autoscalingData.process && e.envName === autoscalingData.envName) || [];

        const autoscalingFilterData = (this.localCloudAppData.spec?.envOverlay?.autoscaling || []).filter(e => e.process !== autoscalingData.process || e.envName !== autoscalingData.envName) || [];

        // 没有autoscaling时
        if (!autoscalingWithProcessEnv.length) {
          if (!this.localCloudAppData.spec.envOverlay.autoscaling) {
            this.localCloudAppData.spec.envOverlay.autoscaling = [];
          }
          this.localCloudAppData.spec.envOverlay.autoscaling.push(autoscalingData);
        } else {
          // 有autoscaling数据
          autoscalingWithProcessEnv.forEach((e) => {
            if (e.process === autoscalingData.process && e.envName === autoscalingData.envName) {
              e.minReplicas = autoscalingData.minReplicas;
              e.maxReplicas = autoscalingData.maxReplicas;
            }
          });
          this.localCloudAppData.spec.envOverlay.autoscaling = [...autoscalingFilterData, ...autoscalingWithProcessEnv];
        }

        // // replicas做一次备份
        // if (this.localCloudAppData.spec.processes[this.btnIndex].replicas) {
        //   this.formDataBackUp.replicas = this.localCloudAppData.spec.processes[this.btnIndex].replicas;
        // }
        // // 需要删除手动调节相关信息
        // delete this.localCloudAppData.spec.processes[this.btnIndex].replicas;
        // 过滤当前进程当前环境envOverlay中replicas
        const { envOverlay } = this.localCloudAppData.spec;
        this.handleFilterAutoscalingData(envOverlay, this.processNameActive); // 传入envOverlay、当前进程名
      } else {
        // // 手动调节
        // // autoscaling做一次备份
        // if (this.localCloudAppData.spec.processes[this.btnIndex].autoscaling) {
        //   this.formDataBackUp.autoscaling = this.localCloudAppData.spec.processes[this.btnIndex].autoscaling;
        // }
        // // 需要删除当前进程base中的autoscaling
        // delete this.localCloudAppData.spec.processes[this.btnIndex].autoscaling;
        // 过滤当前进程当前环境envOverlay中autoscaling
        const { envOverlay } = this.localCloudAppData.spec;
        // // eslint-disable-next-line max-len
        this.handleFilterAutoscalingData(envOverlay, this.processNameActive); // 传入envOverlay、当前进程名
      }

      // 将最大值最小值改为数字类型
      // (this.localCloudAppData.spec?.processes || []).forEach((e) => {
      //   if (e.autoscaling) {
      //     e.autoscaling.minReplicas = e.autoscaling.minReplicas ? Number(e.autoscaling.minReplicas) : '';
      //     e.autoscaling.maxReplicas = e.autoscaling.maxReplicas ? Number(e.autoscaling.maxReplicas) : '';
      //   }
      // });

      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
    },

    // 镜像选择
    handleImageChange() {
      if (this.bkappAnnotations[this.imageCrdlAnnoKey]) {
        this.$set(this.localCloudAppData.metadata, 'annotations', this.bkappAnnotations);
        this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
      }
    },

    async getQuotaPlans() {
      try {
        this.quotaPlansFlag = true;
        const res = await this.$store.dispatch('deploy/fetchQuotaPlans', {});
        this.resQuotaData = res.map(item => item.name);
        // 资源配额数据
        this.allQuotaList = res;
        // 当前stag资源配额
        this.handleChange(this.extraConfigData.stag.resQuotaPlan?.plan || 'default', 'stag');
        // 当前prod资源配额
        this.handleChange(this.extraConfigData.prod.resQuotaPlan?.plan || 'default', 'prod');
        // this.extraConfigData[env].limit = data.limit;
        // this.extraConfigData[env].request = data.request;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.quotaPlansFlag = false;
      }
    },

    // 跳转模块信息
    handleToModuleInfo() {
      this.$store.commit('cloudApi/updateModuleInfoEdit', true);
      this.$emit('tab-change', 'moduleInfo');
    },

    // 查看指南
    handleViewGuide() {
      this.$refs.userGuideRef.showSideslider();
    },

    // 资源配额方案change回调
    handleChange(name, env) {
      if (env === 'stag') {
        this.stagQuotaData = this.allQuotaList.find(v => v.name === name) || { limit: {}, request: {} };
      } else {
        this.prodQuotaData = this.allQuotaList.find(v => v.name === name) || { limit: {}, request: {} };
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.process-container {
  // margin-top: 20px;
  // border: 1px solid #e6e9ea;
  border-top: none;
  padding-bottom: 20px;
}
.tab-container {
  position: relative;
  line-height: 50px;
  height: 50px;
  .tab-list {
    display: flex;
    align-items: center;
    background: #fafbfd;
    border: 1px solid #dcdee5;
    border-left: none;
    border-right: none;
    height: 52px;
    .tab-item {
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
    .isActive {
      border-bottom: 2px solid #fff;
      border-top: 1px solid #dcdee5;
      background: #fff;
      color: #3a84ff;
      cursor: default;
    }
    .add-icon {
      font-size: 18px;
      padding-left: 10px;
      cursor: pointer;
    }
  }
}
.tab-container .bk-tab-label-wrapper .bk-tab-label-list .bk-tab-label-item {
  padding: 0 18px;
  margin-right: 0px;
}

.form-deploy {
  margin: 10px 40px 20px;
  .item-title {
    font-weight: Bold;
    font-size: 14px;
    color: #313238;
    margin: 24px 0;
  }
  .whole-item-tips {
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
  .create-item {
    padding-bottom: 10px;
    .form-group-dir {
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
      .form-group-flex {
        width: 520px;
        margin-top: 10px;
      }
    }
  }
  .form-resource {
    .form-resource-flex {
      display: flex;
    }
  }

  .form-pre {
    border-top: 1px solid #dcdee5;
  }

  .form-pre-command.bk-form.bk-inline-form .bk-form-input {
    height: 32px !important;
  }

  .form-process {
    width: 625px;
  }
}
.btn-container {
  padding: 0 24px;
  .bk-button-group-cls {
    display: flex !important;
    align-items: center;
    max-width: calc(100% - 85px);
    flex-flow: wrap;
    .item-close-icon {
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
.form-detail {
  .form-text {
    color: #313238;
    padding-left: 10px;
  }
}
.w885 {
  width: 885px !important;
}
.env-name {
  width: 420px;
  color: #313238;
  font-size: 14px;
  height: 32px;
  line-height: 32px;
  background: #f0f1f5;
  padding-left: 20px;
}

.env-item {
  background: #fafbfd;
  height: 180px;
  /deep/ .bk-form-item {
    margin-top: 10px;
  }
}
.form-first-cls {
  margin-top: 0 !important;
  padding-top: 10px;
}
.env-container {
  width: 885px;
  background: #f5f7fa;
  border-radius: 2px;
  padding: 20px 24px;
}
.process-name {
  width: 280px;
  height: 140px;
}

.form-envs {
  /deep/ .tooltips-icon {
    right: 540px !important;
    top: 7px !important;
  }
}
.process-btn-wrapper {
  margin-left: 80px;
}
.image-store-icon {
  margin-left: 5px;
  cursor: pointer;
  color: #3a84ff;
}
</style>
