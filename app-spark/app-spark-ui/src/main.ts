import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { subEnv } from '@blueking/sub-saas'
import router from './router';
import App from './app.vue';
import IframeApp from './iframe-app.vue';
import './css/index.css';

// 全量引入 bkui-vue
import bkui from 'bkui-vue';
// 全量引入 bkui-vue 样式
import 'bkui-vue/dist/style.css';

createApp(subEnv ? IframeApp : App)
  .use(router)
  .use(createPinia())
  .use(bkui)
  .mount('.app');
