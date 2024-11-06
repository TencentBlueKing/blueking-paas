# Generated by Django 3.2.25 on 2024-11-05 10:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_transfer_op'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminoperationrecord',
            name='operation',
            field=models.CharField(choices=[('create', '新建'), ('delete', '删除'), ('modify', '修改'), ('create_app', '创建应用'), ('online_to_market', '发布到应用市场'), ('offline_from_market', '从应用市场下架'), ('modify_market_info', '完善应用市场配置'), ('modify_market_url', '修改应用市场访问地址'), ('modify_basic_info', '修改基本信息'), ('start', '启动'), ('stop', '停止'), ('scale', '扩缩容'), ('enable', '启用'), ('disable', '停用'), ('apply', '申请'), ('renew', '续期'), ('deploy', '部署'), ('offline', '下架'), ('switch', '切换资源方案'), ('modify_user_feature_flag', '修改用户特性'), ('switch_default_cluster', '切换默认集群'), ('bind_cluster', '切换绑定集群'), ('modify_log_config', '日志采集管理'), ('provision_instance', '分配增强服务实例'), ('recycle_resource', '回收增强服务实例')], max_length=32, verbose_name='操作类型'),
        ),
        migrations.AlterField(
            model_name='adminoperationrecord',
            name='target',
            field=models.CharField(choices=[('app', '应用'), ('module', '模块'), ('process', '进程'), ('env_var', '环境变量'), ('addon', '增强服务'), ('cloud_api', '云 API 权限'), ('secret', '密钥'), ('app_domain', '访问地址'), ('app_member', '应用成员'), ('build_config', '构建配置'), ('volume_mount', '挂载卷'), ('service_discovery', '服务发现'), ('domain_resolution', '域名解析'), ('deploy_restriction', '部署限制'), ('exit_ip', '出口 IP'), ('access_control', '用户限制'), ('cluster', '集群'), ('process_spec_plan', '应用资源方案'), ('bkplugin_tag', '插件分类'), ('bkplugin_distributor', '插件使用方'), ('document', '文档'), ('deploy_failure_tips', '部署失败提示'), ('source_type_spec', '代码库配置'), ('shared_cert', '共享证书'), ('addon_plan', '增强服务方案'), ('plat_user', '平台用户'), ('feature_flag', '特性标记'), ('egress_spec', 'Egress 配置'), ('template', '模板'), ('dashboard_template', '仪表盘模板'), ('buildpack', 'Buildpack'), ('slugbuilder', 'Slugbuilder'), ('slugrunner', 'Slugrunner')], max_length=32, verbose_name='操作对象'),
        ),
        migrations.AlterField(
            model_name='appoperationrecord',
            name='operation',
            field=models.CharField(choices=[('create', '新建'), ('delete', '删除'), ('modify', '修改'), ('create_app', '创建应用'), ('online_to_market', '发布到应用市场'), ('offline_from_market', '从应用市场下架'), ('modify_market_info', '完善应用市场配置'), ('modify_market_url', '修改应用市场访问地址'), ('modify_basic_info', '修改基本信息'), ('start', '启动'), ('stop', '停止'), ('scale', '扩缩容'), ('enable', '启用'), ('disable', '停用'), ('apply', '申请'), ('renew', '续期'), ('deploy', '部署'), ('offline', '下架'), ('switch', '切换资源方案'), ('modify_user_feature_flag', '修改用户特性'), ('switch_default_cluster', '切换默认集群'), ('bind_cluster', '切换绑定集群'), ('modify_log_config', '日志采集管理'), ('provision_instance', '分配增强服务实例'), ('recycle_resource', '回收增强服务实例')], max_length=32, verbose_name='操作类型'),
        ),
        migrations.AlterField(
            model_name='appoperationrecord',
            name='target',
            field=models.CharField(choices=[('app', '应用'), ('module', '模块'), ('process', '进程'), ('env_var', '环境变量'), ('addon', '增强服务'), ('cloud_api', '云 API 权限'), ('secret', '密钥'), ('app_domain', '访问地址'), ('app_member', '应用成员'), ('build_config', '构建配置'), ('volume_mount', '挂载卷'), ('service_discovery', '服务发现'), ('domain_resolution', '域名解析'), ('deploy_restriction', '部署限制'), ('exit_ip', '出口 IP'), ('access_control', '用户限制'), ('cluster', '集群'), ('process_spec_plan', '应用资源方案'), ('bkplugin_tag', '插件分类'), ('bkplugin_distributor', '插件使用方'), ('document', '文档'), ('deploy_failure_tips', '部署失败提示'), ('source_type_spec', '代码库配置'), ('shared_cert', '共享证书'), ('addon_plan', '增强服务方案'), ('plat_user', '平台用户'), ('feature_flag', '特性标记'), ('egress_spec', 'Egress 配置'), ('template', '模板'), ('dashboard_template', '仪表盘模板'), ('buildpack', 'Buildpack'), ('slugbuilder', 'Slugbuilder'), ('slugrunner', 'Slugrunner')], max_length=32, verbose_name='操作对象'),
        ),
    ]
