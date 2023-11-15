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

#### Get your access_token
Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

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
        "runtime_type": "buildpack"
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

| Parameter Name             | Parameter Type    | Parameter Description                     |
| -------------------------- | ----------------- | ----------------------------------------- |
| id                         | string(uuid)      | UUID                                      |
| repo                       |                   | See the following .repo object description |
| repo_auth_info             |                   | Repository authentication related information |
| web_config                 |                   | Module configuration information for driving client features |
| template_display_name      |                   | Template name used during initialization  |
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
| application                |                   | Application information                   |

Sub-member `.repo` object parameter description:

| Parameter Name         | Parameter Type | Parameter Description                |
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