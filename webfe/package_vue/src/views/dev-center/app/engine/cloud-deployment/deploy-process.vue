<template>
  <div class="deploy-process-config">
    <!-- 查看模式 & 无进程的情况 -->
    <section
      v-if="isReadOnlyMode && !hasProcess"
      style="margin-top: 38px"
    >
      <bk-exception
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        <p
          class="mt10"
          style="color: #979ba5; font-size: 12px"
        >
          {{ $t('进程配置、钩子命令请在 app_desc.yaml 文件中定义。') }}
        </p>
        <p
          class="guide-link mt15"
          @click="handleViewGuide"
        >
          {{ $t('查看使用指南') }}
        </p>
      </bk-exception>
    </section>
    <template v-else>
      <!-- 进程配置 -->
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="deploy-process-loading"
        :offset-top="0"
        :is-transition="false"
        :offset-left="20"
        class="deploy-action-box"
      >
        <!-- 非镜像模块为查看态 -->
        <bk-alert
          v-if="isReadOnlyMode"
          class="guide-alert-cls"
          type="info"
          :show-icon="false"
        >
          <div
            slot="title"
            class="flex-row align-items-center justify-content-between"
          >
            <span>
              <i class="paasng-icon paasng-remind"></i>
              {{
                $t(
                  '当前模块为 “代码仓库” 类型，仅支持查看进程配置。如需修改，请通过源码中的 app_desc.yaml 文件更改（更改将在部署后生效）'
                )
              }}
            </span>
            <bk-button
              size="small"
              text
              @click="handleViewGuide"
            >
              {{ $t('查看使用指南') }}
            </bk-button>
          </div>
        </bk-alert>
        <div
          class="title-wrapper"
          v-if="!isCreate"
        >
          <span class="title">{{ $t('进程配置') }}</span>
          <div
            v-if="!isPageEdit && !isReadOnlyMode"
            class="edit-container"
            @click="handleEditClick"
          >
            <i class="paasng-icon paasng-edit-2 pl10" />
            {{ $t('编辑') }}
          </div>
          <div
            v-if="isReadOnlyMode"
            class="view-only"
            v-bk-tooltips.right="{
              content: recentOperations,
              disabled: !recentOperations,
            }"
          >
            {{ $t('仅支持查看') }}
          </div>
        </div>
        <div class="process-container">
          <section>
            <process-service
              :data="panels"
              :active="processNameActive"
              :active-data="formData"
              :mode="isPageEdit ? 'edit' : 'view'"
              @add="handleProcessNameEdit"
              @edit="handleProcessNameEdit"
              @delete="handleDelete"
              @change="handleBtnGroupClick"
            />
          </section>
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
                <bk-form-item
                  :label="$t('镜像仓库')"
                  :label-width="labelWidth"
                  v-if="!allowMultipleImage"
                >
                  {{ formData.image || '--' }}
                </bk-form-item>
                <bk-form-item
                  :label="$t('镜像地址')"
                  :required="true"
                  :label-width="labelWidth"
                  :property="'image'"
                  :rules="rules.image"
                  :error-display-type="'normal'"
                  v-else-if="isCustomImage && allowMultipleImage"
                >
                  <bk-input
                    ref="mirrorUrl"
                    v-model="formData.image"
                    style="width: 500px"
                    :placeholder="$t('请输入带标签的镜像仓库')"
                  />
                  <p class="whole-item-tips">
                    {{ $t('请输入镜像仓库，如') }}：
                    <span>
                      {{ GLOBAL.CONFIG.MIRROR_EXAMPLE }}
                    </span>
                  </p>
                  <p :class="['whole-item-tips', localLanguage === 'en' ? '' : 'no-wrap']">
                    <span>{{ $t('镜像应监听“容器端口”处所指定的端口号，或环境变量值 $PORT 来提供 HTTP 服务') }}</span>
                  </p>
                </bk-form-item>

                <bk-form-item
                  :label="$t('启动命令')"
                  :label-width="labelWidth"
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
                    {{ $t("数组类型，示例数据：['/serverctl', 'start']，按回车键分隔每个元素") }}
                  </p>
                </bk-form-item>

                <bk-form-item
                  :label="$t('命令参数')"
                  :label-width="labelWidth"
                  :property="'args'"
                >
                  <bk-tag-input
                    v-model="formData.args"
                    style="width: 500px"
                    ext-cls="tag-extra"
                    :placeholder="$t('留空将使用镜像的默认值')"
                    :allow-create="allowCreate"
                    :allow-auto-match="true"
                    :has-delete-icon="hasDeleteIcon"
                    :paste-fn="copyCommandParameter"
                  />
                  <p class="whole-item-tips">
                    {{ $t("数组类型，示例数据：['--port', '8081']，按回车键分隔每个元素") }}
                  </p>
                </bk-form-item>
                <!-- 进程服务编辑态 -->
                <bk-form-item
                  :label="$t('进程服务')"
                  :label-width="labelWidth"
                >
                  <div class="prcess-servie-item">
                    <!-- 主入口，不能关闭进程服务 -->
                    <bk-switcher
                      v-bk-tooltips="{
                        content: $t('取消访问入口后，才可以关闭进程服务'),
                        disabled: !isCurProcessMainEntry,
                      }"
                      v-model="serviceProcess[formData.name]"
                      theme="primary"
                      :disabled="isCurProcessMainEntry"
                      @change="toggleServiceProcess"
                    ></bk-switcher>
                    <span class="item-tips">
                      <i class="paasng-icon paasng-info-line" />
                      {{
                        $t(
                          '开启后，应用内部通信可通过“进程服务名称 + 服务端口”访问，通信地址可在“部署管理”页面的进程详情中查看。'
                        )
                      }}
                      <a
                        target="_blank"
                        :href="GLOBAL.DOC.PROCESS_SERVICE"
                      >
                        {{ $t('进程服务说明') }}
                      </a>
                    </span>
                  </div>
                </bk-form-item>
                <!-- 开启进程服务，展示端口映射 -->
                <bk-form-item
                  v-if="serviceProcess[formData.name]"
                  :label="$t('端口映射')"
                  :label-width="labelWidth"
                >
                  <div class="port-mapping-wrapper">
                    <port-map-table
                      :name="formData.name"
                      :services="formData.services"
                      :main-entry-data="curProcessMainEntryData"
                      :address="moduleAccessAddress"
                      @change-service="handleChangeService"
                      @delete-service="handleDeleteService"
                      @change-access-entry="changeMainEntry"
                    />
                  </div>
                </bk-form-item>
                <bk-form-item :label-width="70">
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
                <!-- Metric 采集 - 编辑态 -->
                <metric
                  v-if="ifopen"
                  :key="btnIndex"
                  ref="metric"
                  :is-edit="isPageEdit"
                  :data="formData"
                  :dashboard-url="dashboardUrl"
                  @updated-data="handleUpdateMetric"
                  @toggle-metric="toggleMetric"
                  @enable-service="toggleServiceProcess(true)"
                />
                <bk-form-item
                  v-if="ifopen"
                  :label="$t('资源配置')"
                  ext-cls="env-form-item-cls"
                  :label-width="labelWidth"
                >
                  <div class="env-name">{{ $t('预发布环境') }}</div>
                  <div class="env-container">
                    <bk-form
                      ref="formStagEnv"
                      :model="formData.env_overlay.stag"
                      ext-cls="form-envs"
                    >
                      <bk-form-item
                        :label="$t('资源配额方案')"
                        :label-width="labelWidth"
                      >
                        <div class="flex-row align-items-center">
                          <bk-select
                            v-model="formData.env_overlay.stag.plan_name"
                            :disabled="false"
                            style="width: 150px"
                            searchable
                            ext-cls="form-style-cls"
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
                          <quota-popver
                            v-else
                            :data="stagQuotaData"
                          />
                        </div>
                      </bk-form-item>
                      <bk-form-item
                        :label="$t('扩缩容方式')"
                        :label-width="labelWidth"
                      >
                        <section>
                          <bk-radio-group
                            v-model="formData.env_overlay.stag.autoscaling"
                            @change="handleRadioChange('stag')"
                            style="flex: 1"
                          >
                            <bk-radio-button
                              class="radio-cls"
                              :value="false"
                            >
                              {{ $t('手动调节') }}
                            </bk-radio-button>
                            <bk-radio-button
                              class="radio-cls"
                              :value="true"
                              :disabled="!autoScalDisableConfig.stag.ENABLE_AUTOSCALING"
                              v-bk-tooltips="{
                                content: $t(
                                  isCreate
                                    ? '请创建成功后，到“模块配置”页面开启自动调节扩缩容。'
                                    : '该环境暂不支持自动扩缩容'
                                ),
                                disabled: autoScalDisableConfig.stag.ENABLE_AUTOSCALING,
                              }"
                            >
                              {{ $t('自动调节') }}
                            </bk-radio-button>
                          </bk-radio-group>

                          <bk-alert
                            v-if="formData.env_overlay.stag.autoscaling"
                            type="info"
                            class="mt10"
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
                        v-if="formData.env_overlay.stag.autoscaling"
                        :label="$t('触发方式')"
                        :label-width="labelWidth"
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
                        v-if="formData.env_overlay.stag.autoscaling"
                        class="mt20"
                      >
                        <bk-form-item
                          :label="$t('最小副本数')"
                          :label-width="labelWidth"
                          :required="true"
                          :property="'scaling_config.min_replicas'"
                          :rules="rules.stagMinReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.stag.scaling_config.min_replicas"
                            type="number"
                            :max="5"
                            :min="1"
                            style="width: 150px"
                          />
                        </bk-form-item>
                        <bk-form-item
                          :label="$t('最大副本数')"
                          :label-width="labelWidth"
                          :required="true"
                          :property="'scaling_config.max_replicas'"
                          :rules="rules.stagMaxReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.stag.scaling_config.max_replicas"
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
                          :label-width="labelWidth"
                          :required="true"
                          :property="'target_replicas'"
                          :rules="rules.formReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.stag.target_replicas"
                            type="number"
                            :max="5"
                            :min="1"
                            style="width: 150px"
                          />
                        </bk-form-item>
                      </section>
                    </bk-form>
                  </div>
                  <div class="env-name">{{ $t('生产环境') }}</div>
                  <div class="env-container">
                    <bk-form
                      ref="formProdEnv"
                      :model="formData.env_overlay.prod"
                      ext-cls="form-envs"
                    >
                      <bk-form-item
                        :label="$t('资源配额方案')"
                        :label-width="labelWidth"
                      >
                        <div class="flex-row align-items-center">
                          <bk-select
                            v-model="formData.env_overlay.prod.plan_name"
                            :disabled="false"
                            style="width: 150px"
                            searchable
                            ext-cls="form-style-cls"
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
                          <quota-popver
                            v-else
                            :data="prodQuotaData"
                          />
                        </div>
                      </bk-form-item>
                      <bk-form-item
                        :label="$t('扩缩容方式')"
                        :label-width="labelWidth"
                      >
                        <section>
                          <bk-radio-group
                            v-model="formData.env_overlay.prod.autoscaling"
                            @change="handleRadioChange('prod')"
                            style="flex: 1"
                          >
                            <bk-radio-button
                              class="radio-cls"
                              :value="false"
                            >
                              {{ $t('手动调节') }}
                            </bk-radio-button>
                            <bk-radio-button
                              class="radio-cls"
                              :value="true"
                              :disabled="!autoScalDisableConfig.prod.ENABLE_AUTOSCALING"
                              v-bk-tooltips="{
                                content: $t(
                                  isCreate
                                    ? '请创建成功后，到“模块配置”页面开启自动调节扩缩容。'
                                    : '该环境暂不支持自动扩缩容'
                                ),
                                disabled: autoScalDisableConfig.prod.ENABLE_AUTOSCALING,
                              }"
                            >
                              {{ $t('自动调节') }}
                            </bk-radio-button>
                          </bk-radio-group>

                          <bk-alert
                            v-if="formData.env_overlay.prod.autoscaling"
                            type="info"
                            class="mt10"
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
                        v-if="formData.env_overlay.prod.autoscaling"
                        :label="$t('触发方式')"
                        :label-width="labelWidth"
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
                        v-if="formData.env_overlay.prod.autoscaling"
                        class="mt20"
                      >
                        <bk-form-item
                          :label="$t('最小副本数')"
                          :label-width="labelWidth"
                          :required="true"
                          :property="'scaling_config.min_replicas'"
                          :rules="rules.prodMinReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.prod.scaling_config.min_replicas"
                            type="number"
                            :max="5"
                            :min="1"
                            style="width: 150px"
                          />
                        </bk-form-item>
                        <bk-form-item
                          :label="$t('最大副本数')"
                          :label-width="labelWidth"
                          :required="true"
                          :property="'scaling_config.max_replicas'"
                          :rules="rules.prodMaxReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.prod.scaling_config.max_replicas"
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
                          :label-width="labelWidth"
                          :required="true"
                          :property="'target_replicas'"
                          :rules="rules.formReplicas"
                          :error-display-type="'normal'"
                        >
                          <bk-input
                            v-model="formData.env_overlay.prod.target_replicas"
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
            <bk-form
              :model="formData"
              :label-width="labelWidth"
            >
              <!-- v1alpha1 是镜像地址，v1alpha2是镜像仓库不带tag -->
              <bk-form-item
                v-if="!allowMultipleImage && !isReadOnlyMode"
                :label="`${$t('镜像仓库')}：`"
              >
                <span class="form-text">{{ formData.image || '--' }}</span>
              </bk-form-item>
              <bk-form-item
                v-else-if="isCustomImage && allowMultipleImage"
                :label="`${$t('镜像地址')}：`"
              >
                <span class="form-text">{{ formData.image || '--' }}</span>
              </bk-form-item>
              <bk-form-item
                :label="`${$t('启动命令')}：`"
                v-if="isReadOnlyMode && readonlyStartupCommand"
              >
                <p class="startup-command">{{ readonlyStartupCommand }}</p>
              </bk-form-item>
              <template v-else>
                <bk-form-item :label="`${$t('启动命令')}：`">
                  <span
                    class="process-tag-cls"
                    v-if="formData.command && formData.command.length"
                  >
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
                  <span
                    class="process-tag-cls"
                    v-if="formData.args && formData.args.length"
                  >
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
              </template>
              <!-- 进程服务查看态 -->
              <bk-form-item :label="`${$t('进程服务')}：`">
                <div class="view-process-service">
                  <span :class="['tag', { enable: formData.services?.length }]">
                    {{ formData.services?.length ? $t('已启用') : $t('未启用') }}
                  </span>
                  <span class="item-tips">
                    <i class="paasng-icon paasng-info-line" />
                    {{
                      $t(
                        '开启后，应用内部通信可通过“进程服务名称 + 服务端口”访问，通信地址可在“部署管理”页面的进程详情中查看。'
                      )
                    }}
                    <a
                      target="_blank"
                      :href="GLOBAL.DOC.PROCESS_SERVICE"
                    >
                      {{ $t('进程服务说明') }}
                    </a>
                  </span>
                </div>
              </bk-form-item>
              <bk-form-item
                :label="`${$t('端口映射')}：`"
                v-if="formData.services?.length"
              >
                <div class="port-mapping-wrapper">
                  <port-map-table
                    :services="formData.services"
                    :address="moduleAccessAddress"
                    :mode="'view'"
                  />
                </div>
              </bk-form-item>
              <bk-form-item :label-width="55">
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
              <!-- Metric 采集 - 查看 -->
              <bk-form-item
                :label="`Metric ${$t('采集')}：`"
                v-if="ifopen"
              >
                <span :class="['tag', { enable: formData.monitoring }]">
                  {{ formData.monitoring ? $t('已启用') : $t('未启用') }}
                </span>
                <span class="item-tips">
                  <i class="paasng-icon paasng-info-line" />
                  <span v-html="metricTipsHtml"></span>
                </span>
                <metric-view-mode
                  v-if="formData.monitoring"
                  :data="formData.monitoring ?? {}"
                />
              </bk-form-item>
              <section
                :class="['mt20', 'extra-config-cls', { 'view-status': !isPageEdit }]"
                v-if="ifopen"
              >
                <bk-form-item :label="`${$t('资源配置')}：`">
                  <div class="flex-row env-detail">
                    <div
                      v-for="item in envsData"
                      :key="item.value"
                      class="env-panel"
                      :class="item.value === 'prod' ? 'ml24' : ''"
                    >
                      <div class="env-name">{{ item.label }}</div>
                      <div class="env-item">
                        <bk-form-item
                          :label="`${$t('资源配额方案')}：`"
                          ext-cls="form-first-cls"
                        >
                          <span class="form-text">{{ formData.env_overlay[item.value].plan_name || '--' }}</span>
                          <span slot="tip">
                            <i
                              v-if="quotaPlansFlag"
                              class="paasng-icon paasng-exclamation-circle uv-tips ml10"
                            />
                            <quota-popver
                              v-else
                              :data="item.value === 'stag' ? stagQuotaData : prodQuotaData"
                            />
                          </span>
                        </bk-form-item>

                        <bk-form-item :label="`${$t('扩缩容方式')}：`">
                          <span class="form-text">
                            {{ formData.env_overlay[item.value].autoscaling ? $t('自动调节') : $t('手动调节') }}
                          </span>
                        </bk-form-item>

                        <section v-if="formData.env_overlay[item.value].autoscaling">
                          <bk-form-item :label="`${$t('最小副本数')}：`">
                            <span class="form-text">
                              {{ formData.env_overlay[item.value].scaling_config.min_replicas || '--' }}
                            </span>
                          </bk-form-item>
                          <bk-form-item :label="`${$t('最大副本数')}：`">
                            <span class="form-text">
                              {{ formData.env_overlay[item.value].scaling_config.max_replicas || '--' }}
                            </span>
                          </bk-form-item>
                        </section>
                        <section v-else>
                          <bk-form-item :label="`${$t('副本数量')}：`">
                            <span class="form-text">
                              {{ formData.env_overlay[item.value].target_replicas || '--' }}
                            </span>
                          </bk-form-item>
                        </section>
                      </div>
                    </div>
                  </div>
                </bk-form-item>
              </section>
            </bk-form>
          </div>

          <!-- 探针 -->
          <section v-if="ifopen">
            <probe
              ref="formProbe"
              :process-data="formData"
              :is-edit="isPageEdit"
              @change-form-data="changeProbeFormData"
            />
          </section>

          <!-- 创建应用于与模块需隐藏 -->
          <div
            class="process-btn-wrapper"
            v-if="isPageEdit && isComponentBtn"
          >
            <bk-button
              class="pl20"
              :theme="'primary'"
              @click="handleSave"
            >
              {{ $t('保存') }}
            </bk-button>
            <bk-button
              class="pr20 ml8"
              @click="handleCancel"
            >
              {{ $t('取消') }}
            </bk-button>
          </div>
        </div>
      </paas-content-loader>

      <!-- 分割线 -->
      <div class="dividing-line"></div>

      <!-- 钩子命令-创建应用、模块不展示 -->
      <deploy-hook v-if="!isCreate" />
    </template>

    <!-- 新增/编辑进程 -->
    <bk-dialog
      v-model="processDialog.visiable"
      width="480"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :title="isEditPopup ? $t('编辑进程') : $t('新增进程')"
      :loading="processDialog.loading"
      ext-cls="prcess-dialog-cls"
      @confirm="handleConfirm"
      @cancel="handleDialogCancel"
    >
      <bk-form
        ref="formDialog"
        :model="processDialog"
        form-type="vertical"
      >
        <bk-form-item
          :label="$t('新增类型')"
          v-if="!isEditPopup"
        >
          <div class="process-type-item">
            <bk-radio :checked="true">
              {{ $t('进程') }}
            </bk-radio>
            <p class="tips">{{ $t('适合长时间运行的进程，可暴露外部或内部流量') }}</p>
          </div>
        </bk-form-item>
        <bk-form-item
          :required="true"
          :property="'name'"
          :label="$t('进程名称')"
          :rules="rules.processName"
          :error-display-type="'normal'"
        >
          <bk-input
            class="path-input-cls"
            v-model="processDialog.name"
            @enter="handleConfirm"
          ></bk-input>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

    <!-- 访问地址变更弹窗 -->
    <entry-change-dialog
      v-model="entryDialog.visible"
      ref="entryChangeDialog"
      :config="entryDialog"
      :address="moduleAccessAddress"
      @confirm="saveAppProcessInfo"
    />

    <!-- 指南 -->
    <user-guide ref="userGuideRef" />
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';
import { RESQUOTADATA, ENV_OVERLAY } from '@/common/constants';
import userGuide from './comps/user-guide/index.vue';
import quotaPopver from './comps/quota-popver';
import deployHook from './deploy-hook';
import { TE_MIRROR_EXAMPLE } from '@/common/constants.js';
import probe from './comps/probe/index.vue';
import metric from './comps/metric/index.vue';
import metricViewMode from './comps/metric/view-mode.vue';
import processService from './comps/process-config/process-service.vue';
import portMapTable from './comps/process-config/port-map-table.vue';
import entryChangeDialog from './comps/process-config/entry-change-dialog.vue';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

export default {
  components: {
    userGuide,
    quotaPopver,
    deployHook,
    probe,
    metric,
    metricViewMode,
    processService,
    portMapTable,
    entryChangeDialog,
  },
  props: {
    moduleId: {
      type: String,
      default: '',
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
    cloudFormData: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      panels: [],
      processNameActive: 'web', // 选中的进程名
      btnIndex: 0,
      panelActive: 0,
      formData: {
        name: 'web',
        image: null,
        image_credential_name: null,
        command: [],
        args: [],
        port: 5000,
        env_overlay: ENV_OVERLAY,
        services: [],
      },
      formDataBackUp: {
        name: 'web',
        image: null,
        image_credential_name: null,
        command: [],
        args: [],
        port: 5000,
        env_overlay: ENV_OVERLAY,
        services: [],
      },
      bkappAnnotations: {},
      allowCreate: true,
      hasDeleteIcon: true,
      processData: [],
      processDataBackUp: [],
      isLoading: false,
      dashboardUrl: '',
      rules: {
        image: [
          {
            required: true,
            message: this.$t('该字段是必填项'),
            trigger: 'blur change',
          },
          {
            regex: /^(?:[a-z0-9]+(?:[._-][a-z0-9]+)*\/)*[a-z0-9]+(?:[._-][a-z0-9]+)*:[a-zA-Z0-9._-]+$/,
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
              this.$refs?.formStagEnv?.clearError();
              const minReplicas = Number(v);
              const maxReplicas = Number(this.formData.env_overlay.stag.scaling_config.max_replicas);
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
              this.$refs?.formStagEnv?.clearError();
              const maxReplicas = Number(v);
              const minReplicas = Number(this.formData.env_overlay.stag.scaling_config.min_replicas);
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
              this.$refs?.formProdEnv?.clearError();
              const minReplicas = Number(v);
              const maxReplicas = Number(this.formData.env_overlay.prod.scaling_config.max_replicas);
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
              this.$refs?.formProdEnv?.clearError();
              const maxReplicas = Number(v);
              const minReplicas = Number(this.formData.env_overlay.prod.scaling_config.min_replicas);
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
            validator: (v) => /^[a-z0-9]([-a-z0-9]){1,11}$/.test(v),
            message: `${this.$t('请输入 2-12 个字符的小写字母、数字、连字符，以小写字母开头')}`,
            trigger: 'blur',
          },
        ],
      },
      imageCredential: '',
      targetPortErrTips: '',
      isTargetPortErrTips: false,
      ifopen: false,
      envsData: [
        { value: 'stag', label: this.$t('预发布环境') },
        { value: 'prod', label: this.$t('生产环境') },
      ],
      resQuotaData: RESQUOTADATA,
      processDialog: {
        loading: false,
        visiable: false,
        name: '',
        index: null,
      },
      quotaPlansFlag: false,
      triggerMethodData: ['CPU 使用率'],
      cpuLabel: 'CPU 使用率',
      cpuValue: '85%',
      autoScalDisableConfig: {
        prod: {},
        stag: {},
      },
      tagInputIndex: 0,
      allowMultipleImage: false,
      allQuotaList: [],
      stagQuotaData: {},
      prodQuotaData: {},
      isEditPopup: false,
      serviceProcess: {},
      moduleAccessAddress: '',
      // 访问地址变更
      entryDialog: {
        visible: false,
        entryData: null,
        type: '',
      },
      // 初始访问入口
      initEntryData: null,
      recentOperations: '',
      hasProcess: true,
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    appCode() {
      return this.$route.params.id;
    },
    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit || this.$store.state.cloudApi.processPageEdit;
    },
    curModuleId() {
      return this.curAppModule?.name;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    // 镜像
    isCustomImage() {
      return this.curAppModule?.web_config?.runtime_type === 'custom_image';
    },
    labelWidth() {
      return this.localLanguage === 'en' ? 190 : 150;
    },
    // 非镜像模块、创建模块、应用为查看模式
    isReadOnlyMode() {
      return !this.isCustomImage && !this.isCreate;
    },
    isCurProcessMainEntry() {
      return this.isMainEntry(this.formData.services);
    },
    curProcessMainEntryData() {
      return this.panels.find((v) => this.isMainEntry(v.services));
    },
    // metric tips
    metricTipsHtml() {
      const monitoringDashboard = `<a href="${this.dashboardUrl}" target="_blank">${this.$t('蓝鲸监控仪表盘')}</a>`;
      return this.$t('配置 Metric 采集后，您可以在 {s} 功能中进行配置并查看您的仪表盘。', { s: monitoringDashboard });
    },
    // 只读模式展示的启动命令
    readonlyStartupCommand() {
      return this.formData?.proc_command;
    },
  },
  watch: {
    formData: {
      handler() {
        if (!this.formData.port) this.formData.port = null;
        if (!this.formData.image_credential_name) this.formData.image_credential_name = null;
        if (!this.serviceProcess[this.formData.name]) {
          this.$set(this.serviceProcess, this.formData.name, !!this.formData.services?.length);
        }
      },
      deep: true,
    },
    cloudFormData: {
      handler(data) {
        if (this.isCreate) {
          // 镜像仓库
          if (!this.formData.image) {
            this.$set(this.formData, 'image', data.url);
          }
          // 镜像凭证
          if (!this.formData.image_credential_name) {
            this.$set(this.formData, 'image_credential_name', data.imageCredentialName);
          }

          if (this.formData.image === this.GLOBAL.CONFIG.MIRROR_EXAMPLE) {
            this.formData.command = [];
            this.formData.args = [];
            this.formData.port = 80;
          } else if (this.formData.image === TE_MIRROR_EXAMPLE) {
            this.formData.command = [];
            this.formData.args = [];
            this.formData.port = 5000;
          }
        }
      },
      immediate: true,
    },
  },
  async created() {
    if (this.isCreate) {
      if (!this.processData.length) {
        // 默认为访问入口
        this.formData.services = [
          {
            exposed_type: { name: 'bk/http' },
            name: 'http',
            protocol: 'TCP',
            port: 80,
            target_port: 5000,
          },
        ];
        this.processData.push(this.formData);
        this.processDataBackUp = cloneDeep(this.processData);
        this.panels = cloneDeep(this.processData);
      }
    } else {
      // 非创建应用初始化为查看态
      this.$store.commit('cloudApi/updateProcessPageEdit', false);
      this.$store.commit('cloudApi/updatePageEdit', false);
      // 扩缩容FeatureFlag
      this.getAutoScalFlag('stag');
      this.getAutoScalFlag('prod');
      this.getAppDashboardInfo();
      this.getEntryList();
      this.init();
    }
    if (this.isReadOnlyMode) {
      this.configureDayjsLocale();
      // 查看模式获取最近一条操作记录
      this.getDeploymentOperations();
    }
    // 获取资源配额数据
    await this.getQuotaPlans();
  },
  methods: {
    configureDayjsLocale() {
      dayjs.extend(relativeTime);
      if (this.localLanguage !== 'en') {
        dayjs.locale('zh-cn');
      }
    },
    async init() {
      try {
        this.isLoading = true;
        const res = await this.$store.dispatch('deploy/getAppProcessInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.hasProcess = !!res.proc_specs?.length;
        this.processData = this.formatData(res.proc_specs);
        this.processDataBackUp = cloneDeep(this.processData);
        if (this.processData.length) {
          this.formData = this.processData[this.btnIndex];
          this.processNameActive = this.processData[this.btnIndex].name;
          // 传入的镜像仓库示例
          if (this.imageUrl) {
            this.formData.image = this.imageUrl;
          }
          if (!Object.keys(this.formData.env_overlay).length) {
            this.formData.env_overlay = ENV_OVERLAY;
          }
          this.panels = cloneDeep(this.processData);
        }
        this.$nextTick(() => {
          this.initEntryData = this.getEntryNames();
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
      }
    },
    // 数据初始化
    formatData(processList = []) {
      // 无进程，默认添加 web 进程
      if (!processList.length) {
        processList.push(this.formData);
        this.processNameActive = this.formData.name;
      }

      const firstProcess = processList[0];
      this.$set(this.serviceProcess, firstProcess.name, !!firstProcess.services?.length);

      // 数据格式统一
      processList = processList.map((item) => ({
        ...item,
        services: Array.isArray(item.services) ? item.services : [],
      }));

      return processList;
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
      if (this.GLOBAL.CONFIG.MIRROR_EXAMPLE === 'docker.io/library/nginx') {
        this.formData.command = [];
        this.formData.args = [];
        this.formData.port = 80;
        return;
      }
      this.formData.command = ['bash', '/app/start_web.sh'];
      this.formData.args = [];
      this.formData.port = 5000;
    },

    // 按扭组点击
    handleBtnGroupClick(name, i) {
      // 选中的进程信息
      this.formData = this.processData[i];
      this.processNameActive = name;
      this.btnIndex = i;
      // eslint-disable-next-line no-plusplus
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
        console.error('error', error);
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
        if (this.processDialog.index !== -1) {
          // 编辑进程名
          this.processData[this.processDialog.index].name = this.processDialog.name;
        } else {
          // 新增进程
          // this.allowMultipleImage 共享image、image_credential_name
          if (!this.allowMultipleImage) {
            this.formDataBackUp.image = this.formData.image;
            this.formDataBackUp.image_credential_name = this.formData.image_credential_name;
          }
          this.formData = cloneDeep(this.formDataBackUp);
          this.formData.name = this.processDialog.name;
          this.processData.push(this.formData);
          this.btnIndex = this.panels.length - 1;
          this.processNameActive = this.processDialog.name;
        }
        this.processDialog.visiable = false;
        this.panels = cloneDeep(this.processData);
      } catch (error) {
        console.error('error', error);
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
      this.processData = cloneDeep(this.processDataBackUp);
      this.panels = cloneDeep(this.processData);
      this.formData = this.processData[this.btnIndex];
      this.$store.commit('cloudApi/updateProcessPageEdit', false);
      this.$store.commit('cloudApi/updatePageEdit', false);
    },

    // 编辑进程名称
    handleProcessNameEdit(processName, i = -1) {
      this.isEditPopup = !!processName;
      this.updatedProcessNameValidator(this.isEditPopup);
      this.processDialog.name = this.isEditPopup ? processName : '';
      this.processDialog.index = i; // 如果为-1， 这代表是新增
      this.processDialog.visiable = true;
    },

    updatedProcessNameValidator(flag) {
      this.$refs.formDialog.clearError();
      if (flag) {
        if (this.rules.processName?.length === 3) {
          this.rules.processName.pop();
        }
      } else {
        if (this.rules.processName?.length === 2) {
          this.rules.processName.push({
            validator: (v) => {
              const panelName = this.panels.map((e) => e.name);
              return !panelName.includes(v);
            },
            message: `${this.$t('不允许添加同名进程')}`,
            trigger: 'blur',
          });
        }
      }
    },

    // 删除某个进程
    handleDelete(processName, i = '') {
      this.processData.splice(i, 1);
      // eslint-disable-next-line prefer-destructuring
      this.formData = this.processData[0];
      this.panels = cloneDeep(this.processData);
      this.processNameActive = this.processData[0].name;
      // 删除
      delete this.serviceProcess[processName];
      this.btnIndex = 0;
    },

    // 获取资源配额信息
    async getQuotaPlans() {
      try {
        this.quotaPlansFlag = true;
        const res = await this.$store.dispatch('deploy/fetchQuotaPlans', {});
        // 默认值
        this.resQuotaData = res.map((item) => item.name);

        // 资源配额数据
        this.allQuotaList = res;
        // 当前stag资源配额
        this.handleChange(this.formData.env_overlay?.stag?.plan_name || 'default', 'stag');
        // 当前prod资源配额
        this.handleChange(this.formData.env_overlay?.prod?.plan_name || 'default', 'prod');
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.quotaPlansFlag = false;
      }
    },

    /**
     * 获取扩缩容featureflag
     */
    async getAutoScalFlag(env) {
      try {
        const res = await this.$store.dispatch('deploy/getAutoScalFlagWithEnv', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          env,
        });
        this.autoScalDisableConfig[env] = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 滚动至报错位置
    scrollToErrorPosition() {
      const element = this.$refs.metric.$el;
      if (element) {
        element?.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
      }
    },

    // 处理校验
    async handleValidate() {
      try {
        await this.$refs?.formStagEnv?.validate();
        await this.$refs?.formProdEnv?.validate();
        await this.$refs?.formDeploy?.validate();
        await this.$refs?.formProbe?.probeValidate();
        await this.$refs?.metric?.metricValidate();
        return true;
      } catch (e) {
        console.error(e);
        if (['service_name', 'path'].includes(e.field)) {
          // 当前metric未校验通过，将页面滚动到错误信息位置
          this.scrollToErrorPosition();
        }
        return false;
      }
    },

    // Metric 参数转换
    transformMonitoring(data) {
      data.forEach((item) => {
        if (item.monitoring && Array.isArray(item.monitoring.metric?.params)) {
          const paramsArray = item.monitoring.metric.params;
          const paramsObject = {};
          paramsArray.forEach((param) => {
            paramsObject[param.key] = param.value;
          });
          item.monitoring.metric.params = paramsObject;
        }
      });
      return data;
    },

    // 保存
    async handleSave() {
      const isValidationSuccessful = await this.handleValidate();
      if (!isValidationSuccessful) return;
      // 创建应用或创建模块返回值
      if (this.isCreate) {
        return [...this.processData];
      }
      const saveEntryData = this.getEntryNames();
      // Metric参数处理
      this.processData = this.transformMonitoring(this.processData);
      // 判断是否变更访问地址
      if (!this.isAccessEntryPointChanged(this.initEntryData, saveEntryData)) {
        // 变更访问入口
        this.entryDialog.visible = true;
        this.entryDialog.entryData = saveEntryData;
        this.entryDialog.type = saveEntryData === null ? 'cancel' : 'change';
      } else {
        this.saveAppProcessInfo();
      }
    },

    // 保存进程配置信息
    async saveAppProcessInfo() {
      try {
        await this.$store.dispatch('deploy/saveAppProcessInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params: {
            proc_specs: [...this.processData],
          },
        });
        this.$refs.entryChangeDialog?.handleAfterLeave();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功！'),
        });
        this.$store.commit('cloudApi/updateProcessPageEdit', false);
        this.$store.commit('cloudApi/updatePageEdit', false);
        this.init();
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: error.detail || error.message,
        });
      }
    },

    // 查看指南
    handleViewGuide() {
      this.$refs.userGuideRef.showSideslider();
    },

    // 资源配额方案change回调
    handleChange(name, env) {
      if (env === 'stag') {
        this.stagQuotaData = this.allQuotaList.find((v) => v.name === name) || { limit: {}, request: {} };
      } else {
        this.prodQuotaData = this.allQuotaList.find((v) => v.name === name) || { limit: {}, request: {} };
      }
    },
    // 设置对应探测数据
    changeProbeFormData(config) {
      this.formData.probes[config.key] = config.data;
    },
    // 判断是否为主入口
    isMainEntry(services) {
      if (!services?.length) return false;
      return services.some((service) => ['bk/http', 'bk/grpc'].includes(service.exposed_type?.name));
    },
    // 启停进程
    toggleServiceProcess(falg) {
      if (falg) {
        if (!this.formData.services?.length) {
          this.formData.services.push({
            name: 'http',
            protocol: 'TCP',
            port: 80,
            target_port: 5000,
          });
        }
      } else {
        this.$set(this.formData, 'services', []);
      }
      this.panels = cloneDeep(this.processData);
    },
    // 更新进程服务
    handleChangeService(data) {
      delete data.service.id;
      delete data.service.isEdit;
      if (data.type === 'edit') {
        // 更新
        this.formData.services.splice(data.editIndex, 1, data.service);
      } else {
        this.formData.services.push(data.service);
      }
    },
    handleDeleteService(name) {
      const index = this.formData.services.findIndex((v) => v.name === name);
      this.formData.services.splice(index, 1);
    },
    // 切换主入口
    changeMainEntry(data) {
      const oldMainEntryName = this.curProcessMainEntryData?.name;
      const servieName = data.type === 'set' ? data.row.name : '';
      this.setProcessMainEntry(oldMainEntryName, data.name, servieName, data.exposedType);
      this.panels = cloneDeep(this.processData);
    },
    // 设置主入口数据
    setProcessMainEntry(oldMainEntryName, newMainEntryName, servieName, exposedType) {
      const newExposedType = { name: exposedType }; // 主入口默认值

      // 找到当前旧的主入口进程并将其 services 中的 exposed_type 设置为 null
      if (oldMainEntryName) {
        this.processData.forEach((process) => {
          if (process.name === oldMainEntryName) {
            process.services?.forEach((service) => {
              if (service.exposed_type?.name) {
                service.exposed_type = null;
              }
            });
          }
        });
      }

      // 取消访问入口无需，设置新的入口
      if (!servieName) return;

      // 找到新的主入口进程并将其 services 中的 exposed_type 设置为 newExposedType
      this.processData.forEach((process) => {
        if (process.name === newMainEntryName) {
          process.services?.forEach((service) => {
            if (service.name === servieName) {
              this.$set(service, 'exposed_type', newExposedType);
            }
          });
        }
      });
    },
    getEntryNames() {
      if (!this.curProcessMainEntryData) return null;
      const entry = this.curProcessMainEntryData?.services?.find((v) =>
        ['bk/http', 'bk/grpc'].includes(v.exposed_type?.name)
      );
      return {
        processName: this.curProcessMainEntryData.name,
        servieName: entry.name,
      };
    },
    // 是否变更访问入口
    isAccessEntryPointChanged(entry1, entry2) {
      if (entry1 === null && entry2 === null) return true;
      if (entry1 === null || entry2 === null) return false;
      return entry1.servieName === entry2.servieName && entry1.processName === entry2.processName;
    },
    // 访问地址列表数据
    async getEntryList() {
      try {
        const res = await this.$store.dispatch('entryConfig/getEntryDataList', {
          appCode: this.appCode,
        });
        const module = res.find((module) => module.name === this.curModuleId);
        this.moduleAccessAddress = module?.envs?.prod?.find((env) => env.address.type !== 'custom')?.address?.url || '';
      } catch (e) {
        this.moduleAccessAddress = '';
      }
    },
    // 启停metric
    toggleMetric(data) {
      if (data === null) {
        this.$set(this.formData, 'monitoring', null);
        return;
      }
      this.formData.monitoring = {};
      this.$set(this.formData.monitoring, 'metric', data);
    },
    // 同步metric数据
    handleUpdateMetric(config) {
      const index = this.processData.findIndex((v) => v.name === config.name);
      this.$set(this.processData[index].monitoring.metric, config.key, config.value);
    },
    // 获取仪表盘链接
    async getAppDashboardInfo() {
      try {
        const res = await this.$store.dispatch('baseInfo/getAppDashboardInfo', {
          appCode: this.appCode,
        });
        this.dashboardUrl = res.dashboard_url || '';
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取当前模块最近部署操作
    async getDeploymentOperations() {
      try {
        const res = await this.$store.dispatch('deploy/getDeployHistory', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          pageParams: {
            limit: 1,
            offset: 0,
          },
        });
        const operation = res.results[0];
        if (operation) {
          const time = dayjs(operation.created).fromNow(true);
          const env = operation.deployment?.environment === 'prod' ? this.$t('生产环境') : this.$t('预发布环境');
          this.recentOperations = this.$t('更新时间：{t}前，来源于{e}部署。', { t: time, e: env });
        }
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.guide-alert-cls {
  margin: 0 24px;
  margin-bottom: 16px;
  i {
    margin-right: 5px;
    font-size: 14px;
    color: #3a84ff;
    transform: translateY(0px);
  }
  /deep/ .bk-alert-wraper {
    height: 32px;
    align-items: center;
    font-size: 12px;
    color: #63656e;
  }
  /deep/ .bk-button-text.bk-button-small {
    padding: 0;
  }
}
.process-container {
  border-top: none;
  .port-mapping-wrapper {
    margin-right: 56px;
  }
  .service-explain {
    padding: 0;
  }
  .item-tips {
    color: #63656e;
    font-size: 12px;
    margin-left: 16px;
    i {
      font-size: 14px;
      color: #979ba5;
      transform: translateY(0px);
    }
    span {
      margin-left: 3px;
    }
  }
}
.ml24 {
  margin-left: 24px;
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
  .prcess-servie-item {
    display: flex;
    align-items: center;
    font-size: 12px;
    color: #63656e;
    .bk-switcher {
      flex-shrink: 0;
    }
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
  .startup-command {
    padding-right: 24px;
  }
  .form-text {
    color: #313238;
  }
  .process-tag-cls .bk-tag:first-child {
    margin-left: 0px;
  }
  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
    font-size: 12px;
    color: #63656e;
    background: #f0f1f5;
    border-radius: 2px;
    &.enable {
      color: #14a568;
      background: #e4faf0;
    }
  }
}
.env-name {
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
  background: #fafbfd;
  border-radius: 2px;
  padding: 20px 24px;
}
.view-status {
  .env-panel {
    width: 420px;
    /deep/ .env-item {
      .bk-form-item .bk-label {
        padding-right: 0;
      }
    }
  }
}
.env-form-item-cls {
  margin-right: 56px;
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
  margin-left: 150px;
}
.image-store-icon {
  margin-left: 5px;
  cursor: pointer;
  color: #3a84ff;
}
.title-wrapper {
  display: flex;
  color: #313238;
  line-height: 22px;
  padding: 0 24px;
  margin-bottom: 12px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
  .edit-container {
    color: #3a84ff;
    font-size: 12px;
    cursor: pointer;
    padding-left: 10px;
  }
  .view-only {
    margin-left: 6px;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
    background: #f0f1f5;
    border-radius: 2px;
    font-size: 12px;
    color: #4d4f56;
  }
}
.more-config-item .bk-form-content {
  margin-left: 55px !important;
}
.form-style-cls {
  background-color: #fff;
}
.process-type-item {
  display: flex;
  align-items: center;
  min-height: 40px;
  background: #e1ecff;
  border: 1px solid #3a84ff;
  border-radius: 2px;
  padding: 0 12px;
  .tips {
    flex: 1;
    padding-left: 16px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }
}
/deep/ .prcess-dialog-cls .bk-dialog .bk-dialog-header {
  padding-bottom: 5px;
}
.dividing-line {
  height: 1px;
  margin: 24px;
  background: #eaebf0;
}
</style>
