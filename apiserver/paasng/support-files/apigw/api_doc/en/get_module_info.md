### Description
View application module information

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description   |
| -------------- | -------------- | -------- | ----------------------- |
| app_code       | string         | Yes      | Application ID          |
| module         | string         | Yes      | Module name, e.g. "default" |

#### 2. API Parameters:
None.

### Request Example

```bash
curl -X POST -H 'X-BKAPI-AUTHORIZATION: {"access_token": "{{Fill in your AccessToken}}"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{{Fill in your AppCode}}/modules/{{Fill in your module name}}/
```

### Response Result Example
```json
{
    "id": "01234567-89ab-cdef-0123-456789abcdef",
    "repo": {
        "source_type": "git",
        "type": "git",
        "trunk_url": "http://example.com/foo/bar.git",
        "repo_url": "http://example.com/foo/bar.git",
        "source_dir": "",
        "repo_fullname": "foo/bar",
        "diff_feature": {
            "method": "external",
            "enabled": true
        },
        "linked_to_internal_svn": false,
        "display_name": "Git"
    },
    "repo_auth_info": {},
    "web_config": {
        "templated_source_enabled": true,
        "runtime_type": "buildpack",
        "build_method": "buildpack",
        "artifact_type": "image"
    },
    "clusters": {
        "prod": {
            "name": "default-main",
            "type": "normal",
            "is_default": true,
            "bcs_cluster_id": "BCS-K8S-00000",
            "support_bcs_metrics": false,
            "ingress_config": {
                "sub_path_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "app_root_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "frontend_ingress_ip": "",
                "default_ingress_domain_tmpl": "%s.apps.example.com",
                "port_map": {
                    "http": 80,
                    "https": 443
                }
            },
            "feature_flags": {
                "ENABLE_MOUNT_LOG_TO_HOST": true,
                "INGRESS_USE_REGEX": true,
                "ENABLE_BK_MONITOR": true,
                "ENABLE_BK_LOG_COLLECTOR": true,
                "ENABLE_AUTOSCALING": false,
                "ENABLE_BCS_EGRESS": false
            }
        },
        "stag": {
            "name": "default-main",
            "type": "normal",
            "is_default": true,
            "bcs_cluster_id": "BCS-K8S-00000",
            "support_bcs_metrics": false,
            "ingress_config": {
                "sub_path_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "app_root_domains": [
                    {
                        "name": "apps.example.com",
                        "reserved": false,
                        "https_enabled": false
                    }
                ],
                "frontend_ingress_ip": "",
                "default_ingress_domain_tmpl": "%s.apps.example.com",
                "port_map": {
                    "http": 80,
                    "https": 443
                }
            },
            "feature_flags": {
                "ENABLE_MOUNT_LOG_TO_HOST": true,
                "INGRESS_USE_REGEX": true,
                "ENABLE_BK_MONITOR": true,
                "ENABLE_BK_LOG_COLLECTOR": true,
                "ENABLE_AUTOSCALING": false,
                "ENABLE_BCS_EGRESS": false
            }
        }
    },
    "template_display_name": "Django with auth",
    "source_origin": 1,
    "region": "ieod",
    "created": "2022-01-01 12:00:00",
    "updated": "2022-01-01 12:00:00",
    "owner": "{username}",
    "name": "default",
    "is_default": true,
    "language": "Python",
    "source_init_template": "dj2_with_auth",
    "exposed_url_type": 2,
    "user_preferred_root_domain": null,
    "last_deployed_date": "2022-01-01 12:00:00",
    "creator": "{username}",
    "application": "01234567-89ab-cdef-0123-456789abcdef"
}
```

### Response Result Parameter Description

| Field                      | Type              | Description                               |
| -------------------------- | ----------------- | ----------------------------------------- |
| id                         | string(uuid)      | UUID                                      |
| repo                       | object            | See the following .repo object description |
| repo_auth_info             | object            | Repository authentication related information |
| web_config                 | object            | Module configuration information for driving client features |
| clusters                   | object            | Clusters infomation.                      | 
| template_display_name      | string            | Template name used during initialization  |
| source_origin              | integer           | Module source code origin, e.g. 1 for Git and other code repositories |
| region                     | string            | Deployment region                         |
| created                    | string(date-time) | Creation time                             |
| updated                    | string(date-time) | Update time                               |
| name                       | string            | Module name                               |
| is_default                 | boolean           | Whether it is the default module          |
| language                   | string            | Programming language                      |
| source_init_template       | string            | Initialization template type              |
| exposed_url_type           | integer           | Type of exposed access                    |
| user_preferred_root_domain | string            | User preferred root domain                |
| last_deployed_date         | string(date-time) | Last deployment time                      |
| application                | string            | Application information                   |

Sub-member `.repo` object parameter description:

| Field                  | Type           | Description                          |
| ---------------------- | -------------- | ------------------------------------ |
| source_type            | string         | Source code type name                |
| type                   | string         | Same as source_type                  |
| trunk_url              | string         | [Deprecated] For SVN source system only |
| repo_url               | string         | Source code repository address       |
| source_dir             | string         | Source code directory                |
| repo_fullname          | string         | Repository name                      |
| diff_feature           | object         | Configuration fields related to "View Source Code Difference" feature |
| linked_to_internal_svn | boolean        | [Deprecated] Reserved field related to SVN |
| display_name           | string         | Display name of the source code system |

Sub-memeber `.web_config` object description
| Field | Type | Description |
| ---------------------- | -------------- | ------------------------------------ |
|templated_source_enabled| boolean | Whether the module uses a source code template |
|runtime_type            | string | Build types, such as buildpack, dockerfile |
|build_method            | string | Build methods, such as buildpack, dockerfile |
|artifact_type           | string | Artifact type |