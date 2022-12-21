# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from bkapi_client_core.apigateway import APIGatewayClient, Operation, OperationGroup, bind_property


class Group(OperationGroup):
    # 创建数据接入（接入到数据平台）
    access_bk_data_by_result_table = bind_property(
        Operation,
        name="access_bk_data_by_result_table",
        method="POST",
        path="/access_bk_data_by_result_table/",
    )

    # 新增告警屏蔽
    add_shield = bind_property(
        Operation,
        name="add_shield",
        method="POST",
        path="/add_shield/",
    )

    # 申请APM数据源
    apply_apm_datasource = bind_property(
        Operation,
        name="apply_apm_datasource",
        method="POST",
        path="/apply_apm_datasource/",
    )

    # 检查实时策略对应的kafka是否存在
    check_or_create_kafka_storage = bind_property(
        Operation,
        name="check_or_create_kafka_storage",
        method="POST",
        path="/check_or_create_kafka_storage/",
    )

    # 创建APM应用
    create_apm_application = bind_property(
        Operation,
        name="create_apm_application",
        method="POST",
        path="/create_apm_application/",
    )

    # 快速创建APM应用
    apm_create_application = bind_property(
        Operation,
        name="apm_create_application",
        method="POST",
        path="/apm/create_application/",
    )

    # 创建自定义指标
    create_custom_time_series = bind_property(
        Operation,
        name="create_custom_time_series",
        method="POST",
        path="/create_custom_time_series/",
    )

    # 创建结果表快照配置
    create_result_table_snapshot = bind_property(
        Operation,
        name="create_result_table_snapshot",
        method="POST",
        path="/metadata_create_result_table_snapshot/",
    )

    # 自定义指标列表
    custom_time_series = bind_property(
        Operation,
        name="custom_time_series",
        method="GET",
        path="/custom_time_series/",
    )

    # 自定义指标详情
    custom_time_series_detail = bind_property(
        Operation,
        name="custom_time_series_detail",
        method="GET",
        path="/custom_time_series_detail/",
    )

    # 删除处理套餐
    delete_action_config = bind_property(
        Operation,
        name="delete_action_config",
        method="POST",
        path="/delete_action_config/",
    )

    # 删除告警策略
    delete_alarm_strategy = bind_property(
        Operation,
        name="delete_alarm_strategy",
        method="POST",
        path="/delete_alarm_strategy/",
    )

    # 删除告警策略
    delete_alarm_strategy_v2 = bind_property(
        Operation,
        name="delete_alarm_strategy_v2",
        method="POST",
        path="/delete_alarm_strategy_v2/",
    )

    # 删除告警策略
    delete_alarm_strategy_v3 = bind_property(
        Operation,
        name="delete_alarm_strategy_v3",
        method="POST",
        path="/delete_alarm_strategy_v3/",
    )

    # 应用
    delete_apm_app_config = bind_property(
        Operation,
        name="delete_apm_app_config",
        method="POST",
        path="/delete_apm_delete_app_config/",
    )

    # 删除通知组
    delete_notice_group = bind_property(
        Operation,
        name="delete_notice_group",
        method="POST",
        path="/delete_notice_group/",
    )

    # 删除快照回溯配置
    delete_restore_result_table_snapshot = bind_property(
        Operation,
        name="delete_restore_result_table_snapshot",
        method="POST",
        path="/metadata_delete_restore_result_table_snapshot/",
    )

    # 删除结果表快照配置
    delete_result_table_snapshot = bind_property(
        Operation,
        name="delete_result_table_snapshot",
        method="POST",
        path="/metadata_delete_result_table_snapshot/",
    )

    # 应用详情
    detail_apm_application = bind_property(
        Operation,
        name="detail_apm_application",
        method="GET",
        path="/detail_apm_application/",
    )

    # 解除告警屏蔽
    disable_shield = bind_property(
        Operation,
        name="disable_shield",
        method="POST",
        path="/disable_shield/",
    )

    # 编辑处理套餐
    edit_action_config = bind_property(
        Operation,
        name="edit_action_config",
        method="POST",
        path="/edit_action_config/",
    )

    # 编辑告警屏蔽
    edit_shield = bind_property(
        Operation,
        name="edit_shield",
        method="POST",
        path="/edit_shield/",
    )

    # 查询指定ES快照仓库
    es_snapshot_repository = bind_property(
        Operation,
        name="es_snapshot_repository",
        method="GET",
        path="/metadata_es_snapshot_repository/",
    )

    # 导出拨测任务配置
    export_uptime_check_task = bind_property(
        Operation,
        name="export_uptime_check_task",
        method="GET",
        path="/export_uptime_check_task/",
    )

    # 根据table_id补充cmdb节点信息
    full_cmdb_node_info = bind_property(
        Operation,
        name="full_cmdb_node_info",
        method="POST",
        path="/full_cmdb_node_info/",
    )

    # 获取处理套餐
    get_action_config = bind_property(
        Operation,
        name="get_action_config",
        method="GET",
        path="/get_action_config/",
    )

    # 获取BCS集群灰度ID名单
    get_bcs_gray_cluster_list = bind_property(
        Operation,
        name="get_bcs_gray_cluster_list",
        method="GET",
        path="/get_bcs_gray_cluster_list/",
    )

    # 采集配置列表
    get_collect_config_list = bind_property(
        Operation,
        name="get_collect_config_list",
        method="GET",
        path="/get_collect_config_list/",
    )

    # 查询采集配置节点状态
    get_collect_status = bind_property(
        Operation,
        name="get_collect_status",
        method="GET",
        path="/get_collect_status/",
    )

    # 获取监控链路时序数据
    get_es_data = bind_property(
        Operation,
        name="get_es_data",
        method="POST",
        path="/get_es_data/",
    )

    # 查询事件流转记录
    get_event_log = bind_property(
        Operation,
        name="get_event_log",
        method="GET",
        path="/get_event_log/",
    )

    # 快照回溯状态
    get_restore_result_table_snapshot_state = bind_property(
        Operation,
        name="get_restore_result_table_snapshot_state",
        method="POST",
        path="/metadata_get_restore_result_table_snapshot_state/",
    )

    # 验证ES快照仓库
    get_result_table_snapshot_state = bind_property(
        Operation,
        name="get_result_table_snapshot_state",
        method="POST",
        path="/metadata_get_result_table_snapshot_state/",
    )

    # 获取配置管理组和告警接收组相关数据
    get_setting_and_notify_group = bind_property(
        Operation,
        name="get_setting_and_notify_group",
        method="GET",
        path="/get_setting_and_notify_group/",
    )

    # 获取告警屏蔽
    get_shield = bind_property(
        Operation,
        name="get_shield",
        method="GET",
        path="/get_shield/",
    )

    # 查询运营数据
    get_statistics_by_json = bind_property(
        Operation,
        name="get_statistics_by_json",
        method="GET",
        path="/get_statistics_by_json/",
    )

    # 获取监控链路时序数据
    get_ts_data = bind_property(
        Operation,
        name="get_ts_data",
        method="POST",
        path="/get_ts_data",
    )

    # 拨测节点列表
    get_uptime_check_node_list = bind_property(
        Operation,
        name="get_uptime_check_node_list",
        method="GET",
        path="/get_uptime_check_node_list/",
    )

    # 拨测任务列表
    get_uptime_check_task_list = bind_property(
        Operation,
        name="get_uptime_check_task_list",
        method="GET",
        path="/get_uptime_check_task_list/",
    )

    # 获取变量
    get_variable_field = bind_property(
        Operation,
        name="get_variable_field",
        method="GET",
        path="/get_variable_field/",
    )

    # 获取变量
    get_variable_value = bind_property(
        Operation,
        name="get_variable_value",
        method="POST",
        path="/get_variable_value/",
    )

    # 查询组内人员
    group_list = bind_property(
        Operation,
        name="group_list",
        method="GET",
        path="/group_list/",
    )

    # 导入拨测节点配置
    import_uptime_check_node = bind_property(
        Operation,
        name="import_uptime_check_node",
        method="POST",
        path="/import_uptime_check_node/",
    )

    # 导入拨测任务配置
    import_uptime_check_task = bind_property(
        Operation,
        name="import_uptime_check_task",
        method="POST",
        path="/import_uptime_check_task/",
    )

    # 是否超级管理员
    is_superuser = bind_property(
        Operation,
        name="is_superuser",
        method="POST",
        path="/is_superuser/",
    )

    # 应用列表
    list_apm_application = bind_property(
        Operation,
        name="list_apm_application",
        method="GET",
        path="/list_apm_application/",
    )

    # 应用
    list_apm_es_cluster_info = bind_property(
        Operation,
        name="list_apm_es_cluster_info",
        method="GET",
        path="/list_apm_es_cluster_info/",
    )

    # 快照仓库列表
    list_es_snapshot_repository = bind_property(
        Operation,
        name="list_es_snapshot_repository",
        method="POST",
        path="/metadata_list_es_snapshot_repository/",
    )

    # 快照回溯列表
    list_restore_result_table_snapshot = bind_property(
        Operation,
        name="list_restore_result_table_snapshot",
        method="POST",
        path="/metadata_list_restore_result_table_snapshot/",
    )

    # 结果表快照配置列表
    list_result_table_snapshot = bind_property(
        Operation,
        name="list_result_table_snapshot",
        method="POST",
        path="/metadata_list_result_table_snapshot/",
    )

    # 结果表快照配置列表含物理索引
    list_result_table_snapshot_indices = bind_property(
        Operation,
        name="list_result_table_snapshot_indices",
        method="POST",
        path="/metadata_list_result_table_snapshot_indices/",
    )

    # 获取告警屏蔽列表
    list_shield = bind_property(
        Operation,
        name="list_shield",
        method="POST",
        path="/list_shield/",
    )

    # 创建存储集群信息
    metadata_create_cluster_info = bind_property(
        Operation,
        name="metadata_create_cluster_info",
        method="POST",
        path="/metadata_create_cluster_info/",
    )

    # 创建监控数据源
    metadata_create_data_id = bind_property(
        Operation,
        name="metadata_create_data_id",
        method="POST",
        path="/metadata_create_data_id/",
    )

    # 创建统计数据，按指定周期聚合
    metadata_create_down_sample_data_flow = bind_property(
        Operation,
        name="metadata_create_down_sample_data_flow",
        method="POST",
        path="/metadata_create_down_sample_data_flow/",
    )

    # 创建ES快照仓库
    metadata_create_es_snapshot_repository = bind_property(
        Operation,
        name="metadata_create_es_snapshot_repository",
        method="POST",
        path="/metadata_create_es_snapshot_repository/",
    )

    # 创建事件分组
    metadata_create_event_group = bind_property(
        Operation,
        name="metadata_create_event_group",
        method="POST",
        path="/metadata_create_event_group/",
    )

    # 创建监控结果表
    metadata_create_result_table = bind_property(
        Operation,
        name="metadata_create_result_table",
        method="POST",
        path="/metadata_create_result_table/",
    )

    # 创建结果表的维度拆分配置
    metadata_create_result_table_metric_split = bind_property(
        Operation,
        name="metadata_create_result_table_metric_split",
        method="POST",
        path="/metadata_create_result_table_metric_split/",
    )

    # 创建自定义时序分组
    metadata_create_time_series_group = bind_property(
        Operation,
        name="metadata_create_time_series_group",
        method="POST",
        path="/metadata_create_time_series_group/",
    )

    # 删除存储集群信息
    metadata_delete_cluster_info = bind_property(
        Operation,
        name="metadata_delete_cluster_info",
        method="POST",
        path="/metadata_delete_cluster_info/",
    )

    # 删除ES快照仓库
    metadata_delete_es_snapshot_repository = bind_property(
        Operation,
        name="metadata_delete_es_snapshot_repository",
        method="POST",
        path="/metadata_delete_es_snapshot_repository/",
    )

    # 删除事件分组
    metadata_delete_event_group = bind_property(
        Operation,
        name="metadata_delete_event_group",
        method="POST",
        path="/metadata_delete_event_group/",
    )

    # 删除自定义时序分组
    metadata_delete_time_series_group = bind_property(
        Operation,
        name="metadata_delete_time_series_group",
        method="POST",
        path="/metadata_delete_time_series_group/",
    )

    # 转发 es get 请求
    metadata_es_route = bind_property(
        Operation,
        name="metadata_es_route",
        method="POST",
        path="/metadata_es_route/",
    )

    # 查询指定存储集群信息
    metadata_get_cluster_info = bind_property(
        Operation,
        name="metadata_get_cluster_info",
        method="GET",
        path="/metadata_get_cluster_info/",
    )

    # 查询空间类型列表
    metadata_get_clusters_by_space_uid = bind_property(
        Operation,
        name="metadata_get_clusters_by_space_uid",
        method="GET",
        path="/metadata_get_clusters_by_space_uid/",
    )

    # 获取监控数据源具体信息
    metadata_get_data_id = bind_property(
        Operation,
        name="metadata_get_data_id",
        method="GET",
        path="/metadata_get_data_id/",
    )

    # 查询事件分组具体内容
    metadata_get_event_group = bind_property(
        Operation,
        name="metadata_get_event_group",
        method="GET",
        path="/metadata_get_event_group/",
    )

    # 获取监控结果表具体信息
    metadata_get_result_table = bind_property(
        Operation,
        name="metadata_get_result_table",
        method="GET",
        path="/metadata_get_result_table/",
    )

    # 查询指定结果表的指定存储信息
    metadata_get_result_table_storage = bind_property(
        Operation,
        name="metadata_get_result_table_storage",
        method="GET",
        path="/metadata_get_result_table_storage/",
    )

    # 创建空间
    metadata_create_space = bind_property(
        Operation,
        name="metadata_create_space",
        method="POST",
        path="/metadata_create_space/",
    )

    # 查询空间实例详情
    metadata_get_space_detail = bind_property(
        Operation,
        name="metadata_get_space_detail",
        method="GET",
        path="/metadata_get_space_detail/",
    )

    # 获取自定义时序分组具体内容
    metadata_get_time_series_group = bind_property(
        Operation,
        name="metadata_get_time_series_group",
        method="GET",
        path="/metadata_get_time_series_group/",
    )

    # 获取自定义时序结果表的metrics信息
    metadata_get_time_series_metrics = bind_property(
        Operation,
        name="metadata_get_time_series_metrics",
        method="GET",
        path="/metadata_get_time_series_metrics/",
    )

    # 查询结果表MQ的最新数据
    metadata_kafka_tail = bind_property(
        Operation,
        name="metadata_kafka_tail",
        method="GET",
        path="/metadata_kafka_tail/",
    )

    # 查询当前已有的标签信息
    metadata_list_label = bind_property(
        Operation,
        name="metadata_list_label",
        method="GET",
        path="/metadata_list_label/",
    )

    # 查询监控结果表
    metadata_list_result_table = bind_property(
        Operation,
        name="metadata_list_result_table",
        method="GET",
        path="/metadata_list_result_table/",
    )

    # 查询空间类型列表
    metadata_list_space_types = bind_property(
        Operation,
        name="metadata_list_space_types",
        method="GET",
        path="/metadata_list_space_types/",
    )

    # 查询空间实例列表
    metadata_list_spaces = bind_property(
        Operation,
        name="metadata_list_spaces",
        method="GET",
        path="/metadata_list_spaces/",
    )

    # 查询置顶空间列表
    metadata_list_sticky_spaces = bind_property(
        Operation,
        name="metadata_list_sticky_spaces",
        method="GET",
        path="/metadata_list_sticky_spaces/",
    )

    # 获取所有transfer集群信息
    metadata_list_transfer_cluster = bind_property(
        Operation,
        name="metadata_list_transfer_cluster",
        method="GET",
        path="/metadata_list_transfer_cluster/",
    )

    # 修改存储集群信息
    metadata_modify_cluster_info = bind_property(
        Operation,
        name="metadata_modify_cluster_info",
        method="POST",
        path="/metadata_modify_cluster_info/",
    )

    # 修改指定数据源的配置信息
    metadata_modify_data_id = bind_property(
        Operation,
        name="metadata_modify_data_id",
        method="POST",
        path="/metadata_modify_data_id/",
    )

    # 修改数据源与结果表的关系
    metadata_modify_datasource_result_table = bind_property(
        Operation,
        name="metadata_modify_datasource_result_table",
        method="POST",
        path="/metadata_modify_datasource_result_table/",
    )

    # 修改ES快照仓库
    metadata_modify_es_snapshot_repository = bind_property(
        Operation,
        name="metadata_modify_es_snapshot_repository",
        method="POST",
        path="/metadata_modify_es_snapshot_repository/",
    )

    # 修改事件分组
    metadata_modify_event_group = bind_property(
        Operation,
        name="metadata_modify_event_group",
        method="POST",
        path="/metadata_modify_event_group/",
    )

    # 修改监控结果表
    metadata_modify_result_table = bind_property(
        Operation,
        name="metadata_modify_result_table",
        method="POST",
        path="/metadata_modify_result_table/",
    )

    # 修改自定义时序分组
    metadata_modify_time_series_group = bind_property(
        Operation,
        name="metadata_modify_time_series_group",
        method="POST",
        path="/metadata_modify_time_series_group/",
    )

    # 创建事件分组
    metadata_query_event_group = bind_property(
        Operation,
        name="metadata_query_event_group",
        method="GET",
        path="/metadata_query_event_group/",
    )

    # 获取自定义时序分组具体内容
    metadata_query_tag_values = bind_property(
        Operation,
        name="metadata_query_tag_values",
        method="GET",
        path="/metadata_query_tag_values/",
    )

    # 查询事件分组
    metadata_query_time_series_group = bind_property(
        Operation,
        name="metadata_query_time_series_group",
        method="GET",
        path="/metadata_query_time_series_group/",
    )

    # 取消置顶/置顶空间
    metadata_stick_space = bind_property(
        Operation,
        name="metadata_stick_space",
        method="POST",
        path="/metadata_stick_space/",
    )

    # 将指定的监控单业务结果表升级为全业务结果表
    metadata_upgrade_result_table = bind_property(
        Operation,
        name="metadata_upgrade_result_table",
        method="POST",
        path="/metadata_upgrade_result_table/",
    )

    # 验证ES快照仓库
    metadata_verify_es_snapshot_repository = bind_property(
        Operation,
        name="metadata_verify_es_snapshot_repository",
        method="GET",
        path="/metadata_verify_es_snapshot_repository/",
    )

    # 修改自定义指标
    modify_custom_time_series = bind_property(
        Operation,
        name="modify_custom_time_series",
        method="POST",
        path="/modify_custom_time_series/",
    )

    # 修改快照回溯配置
    modify_restore_result_table_snapshot = bind_property(
        Operation,
        name="modify_restore_result_table_snapshot",
        method="POST",
        path="/metadata_modify_restore_result_table_snapshot/",
    )

    # 修改结果表快照配置
    modify_result_table_snapshot = bind_property(
        Operation,
        name="modify_result_table_snapshot",
        method="POST",
        path="/metadata_modify_result_table_snapshot/",
    )

    # 统一查询时序数据
    promql_query = bind_property(
        Operation,
        name="promql_query",
        method="POST",
        path="/promql_query/",
    )

    # 应用
    query_apm_application_config = bind_property(
        Operation,
        name="query_apm_application_config",
        method="GET",
        path="/query_apm_application_config/",
    )

    # 应用
    query_apm_endpoint = bind_property(
        Operation,
        name="query_apm_endpoint",
        method="POST",
        path="/query_apm_endpoint/",
    )

    # 应用
    query_apm_es = bind_property(
        Operation,
        name="query_apm_es",
        method="POST",
        path="/query_apm_es/",
    )

    # 查询apm应用es映射
    query_apm_es_mapping = bind_property(
        Operation,
        name="query_apm_es_mapping",
        method="POST",
        path="/query_apm_es_mapping/",
    )

    # 应用
    query_apm_event = bind_property(
        Operation,
        name="query_apm_event",
        method="POST",
        path="/query_apm_event/",
    )

    # 应用
    query_apm_fields = bind_property(
        Operation,
        name="query_apm_fields",
        method="GET",
        path="/query_apm_fields/",
    )

    # 查询apm主机实例
    query_apm_host_instance = bind_property(
        Operation,
        name="query_apm_host_instance",
        method="POST",
        path="/query_host_instance/",
    )

    # 查询远程服务接口调用关系
    query_apm_remote_service_relation = bind_property(
        Operation,
        name="query_apm_remote_service_relation",
        method="POST",
        path="/query_remote_service_relation/",
    )

    # 应用
    query_apm_root_endpoint = bind_property(
        Operation,
        name="query_apm_root_endpoint",
        method="GET",
        path="/query_apm_root_endpoint/",
    )

    # 应用
    query_apm_span = bind_property(
        Operation,
        name="query_apm_span",
        method="POST",
        path="/query_apm_span/",
    )

    # 应用
    query_apm_topo_instance = bind_property(
        Operation,
        name="query_apm_topo_instance",
        method="POST",
        path="/query_apm_topo_instance/",
    )

    # 应用
    query_apm_topo_node = bind_property(
        Operation,
        name="query_apm_topo_node",
        method="GET",
        path="/query_apm_topo_node/",
    )

    # 应用
    query_apm_topo_relation = bind_property(
        Operation,
        name="query_apm_topo_relation",
        method="GET",
        path="/query_apm_topo_relation/",
    )

    # 应用
    query_apm_trace_detail = bind_property(
        Operation,
        name="query_apm_trace_detail",
        method="POST",
        path="/query_apm_trace_detail/",
    )

    # 应用
    query_apm_trace_list = bind_property(
        Operation,
        name="query_apm_trace_list",
        method="POST",
        path="/query_apm_trace_list/",
    )

    # 查询采集配置
    query_collect_config = bind_property(
        Operation,
        name="query_collect_config",
        method="POST",
        path="/query_collect_config/",
    )

    # BCS集群接入蓝鲸监控
    register_cluster_from_bcs = bind_property(
        Operation,
        name="register_cluster_from_bcs",
        method="POST",
        path="/register_cluster/",
    )

    # 应用
    release_apm_app_config = bind_property(
        Operation,
        name="release_apm_app_config",
        method="POST",
        path="/release_apm_app_config/",
    )

    # rest-api告警推送
    restapi_fault_ingester = bind_property(
        Operation,
        name="restapi_fault_ingester",
        method="POST",
        path="/event/rest_api/",
    )

    # 快照回溯
    restore_result_table_snapshot = bind_property(
        Operation,
        name="restore_result_table_snapshot",
        method="POST",
        path="/metadata_restore_result_table_snapshot/",
    )

    # 保存处理套餐
    save_action_config = bind_property(
        Operation,
        name="save_action_config",
        method="POST",
        path="/save_action_config/",
    )

    # 保存告警策略
    save_alarm_strategy = bind_property(
        Operation,
        name="save_alarm_strategy",
        method="POST",
        path="/save_alarm_strategy/",
    )

    # 保存告警策略
    save_alarm_strategy_v2 = bind_property(
        Operation,
        name="save_alarm_strategy_v2",
        method="POST",
        path="/save_alarm_strategy_v2/",
    )

    # 保存告警策略
    save_alarm_strategy_v3 = bind_property(
        Operation,
        name="save_alarm_strategy_v3",
        method="POST",
        path="/save_alarm_strategy_v3/",
    )

    # 创建/保存采集配置
    save_collect_config = bind_property(
        Operation,
        name="save_collect_config",
        method="POST",
        path="/save_collect_config/",
    )

    # 保存通知组
    save_notice_group = bind_property(
        Operation,
        name="save_notice_group",
        method="POST",
        path="/save_notice_group/",
    )

    # 查询处理记录列表
    search_action = bind_property(
        Operation,
        name="search_action",
        method="POST",
        path="/search_action/",
    )

    # 批量获取处理套餐
    search_action_config = bind_property(
        Operation,
        name="search_action_config",
        method="GET",
        path="/search_action_config/",
    )

    # 查询告警策略
    search_alarm_strategy = bind_property(
        Operation,
        name="search_alarm_strategy",
        method="POST",
        path="/search_alarm_strategy/",
    )

    # 查询告警策略
    search_alarm_strategy_v2 = bind_property(
        Operation,
        name="search_alarm_strategy_v2",
        method="POST",
        path="/search_alarm_strategy_v2/",
    )

    # 查询告警策略
    search_alarm_strategy_v3 = bind_property(
        Operation,
        name="search_alarm_strategy_v3",
        method="POST",
        path="/search_alarm_strategy_v3/",
    )

    # 查询全业务告警策略
    search_alarm_strategy_without_biz = bind_property(
        Operation,
        name="search_alarm_strategy_without_biz",
        method="POST",
        path="/search_alarm_strategy_without_biz/",
    )

    # 查询告警
    search_alert = bind_property(
        Operation,
        name="search_alert",
        method="POST",
        path="/search_alert/",
    )

    search_alert_by_event = bind_property(
        Operation,
        name="search_alert_by_event",
        method="POST",
        path="/search_alert_by_event/",
    )

    # 查询事件
    search_event = bind_property(
        Operation,
        name="search_event",
        method="POST",
        path="/search_event/",
    )

    # 查询通知组
    search_notice_group = bind_property(
        Operation,
        name="search_notice_group",
        method="POST",
        path="/search_notice_group/",
    )

    # 应用
    start_apm_application = bind_property(
        Operation,
        name="start_apm_application",
        method="GET",
        path="/start_apm_application/",
    )

    # 应用
    stop_apm_application = bind_property(
        Operation,
        name="stop_apm_application",
        method="GET",
        path="/stop_apm_application/",
    )

    # 启停告警策略
    switch_alarm_strategy = bind_property(
        Operation,
        name="switch_alarm_strategy",
        method="POST",
        path="/switch_alarm_strategy/",
    )

    # 订阅报表测试
    test_report_mail = bind_property(
        Operation,
        name="test_report_mail",
        method="POST",
        path="/test_report_mail/",
    )

    # 获取指标计算函数
    time_series_functions = bind_property(
        Operation,
        name="time_series_functions",
        method="GET",
        path="/time_series/functions/",
    )

    # 获取时序指标
    time_series_metric = bind_property(
        Operation,
        name="time_series_metric",
        method="POST",
        path="/time_series/metric/",
    )

    # 获取指标层级
    time_series_metric_level = bind_property(
        Operation,
        name="time_series_metric_level",
        method="POST",
        path="/time_series/metric_level/",
    )

    # 统一查询时序数据
    time_series_unify_query = bind_property(
        Operation,
        name="time_series_unify_query",
        method="POST",
        path="/time_series/unify_query/",
    )

    # 应用
    update_apm_metric_fields = bind_property(
        Operation,
        name="update_apm_metric_fields",
        method="POST",
        path="/update_apm_metric_fields/",
    )

    # 批量更新策略局部配置
    update_partial_strategy_v2 = bind_property(
        Operation,
        name="update_partial_strategy_v2",
        method="POST",
        path="/update_partial_strategy_v2/",
    )

    # 批量更新策略局部配置
    update_partial_strategy_v3 = bind_property(
        Operation,
        name="update_partial_strategy_v3",
        method="POST",
        path="/update_partial_strategy_v3/",
    )

    # uwork告警推送
    uwork_fault_ingester = bind_property(
        Operation,
        name="uwork_fault_ingester",
        method="POST",
        path="/event/uwork/",
    )


class Client(APIGatewayClient):
    """bkmonitorv3
    监控平台v3上云版本
    """

    _api_name = "bkmonitorv3"

    api = bind_property(Group, name="api")
