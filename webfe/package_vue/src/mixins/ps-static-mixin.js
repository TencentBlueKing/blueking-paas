/*
* Tencent is pleased to support the open source community by making
* 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
* Copyright (C) 2017-2022THL A29 Limited, a Tencent company.  All rights reserved.
* Licensed under the MIT License (the "License").
* You may not use this file except in compliance with the License.
* You may obtain a copy of the License at http://opensource.org/licenses/MIT
* Unless required by applicable law or agreed to in writing,
* software distributed under the License is distributed on
* an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
* either express or implied. See the License for the
* specific language governing permissions and limitations under the License.
*
* We undertake not to change the open source license (MIT license) applicable
*
* to the current version of the project delivered to anyone in the future.
*/

import { PAAS_STATIC_CONFIG as staticList } from '../../static/json/paas_static.js';

// The header's static infomations mixin
export const psHeaderInfo = {
  data () {
    return {
      headerStaticInfo: staticList.header
    };
  }
};

// The footer's static infomations mixin
export const psFooterInfo = {
  data () {
    return {
      footerStaticInfo: staticList.footer
    };
  }
};

// The homepage's static infomations mixin
export const psIndexInfo = {
  data () {
    return {
      homePageStaticInfo: staticList.index
    };
  }
};

// The App page nav's static infomations mixin
export const psAppNavInfo = {
  data () {
    return {
      appNavStaticInfo: staticList.app_nav
    };
  }
};

// The Service page nav's static infomations mixin
export const psServiceNavInfo = {
  data () {
    return {
      serviceNavStaticInfo: staticList.bk_service
    };
  }
};
