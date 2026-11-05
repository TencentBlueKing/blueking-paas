/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

function shellQuote(value) {
  return `'${value.replace(/'/g, '\'\\\'\'')}'`;
}

function getPythonEnvironment({ apiUrl, environmentMode }) {
  if (environmentMode === 'dotenv') {
    return 'from dotenv import load_dotenv\nload_dotenv()';
  }
  return `os.environ["E2B_API_URL"] = ${JSON.stringify(apiUrl)}
os.environ["E2B_API_KEY"] = "<your-api-key>"`;
}

function getCreateSandboxCode({ templateId, t }) {
  return `# ${t('templateID 取自「沙箱模板」，timeout 为存活秒数')}
sandbox = Sandbox.create(
    template=${JSON.stringify(templateId || '<templateID>')}, timeout=3600,
    api_key=os.environ["E2B_API_KEY"], api_url=os.environ["E2B_API_URL"],
)`;
}

export function buildEnvironmentCode({ apiUrl, environmentMode, t }) {
  const pythonEnvironment = getPythonEnvironment({ apiUrl, environmentMode });
  if (environmentMode === 'dotenv') {
    return `# ${t('在项目根目录创建 .env 文件，写入环境变量：')}
E2B_API_URL=${JSON.stringify(apiUrl)}
E2B_API_KEY="<your-api-key>"

${pythonEnvironment}`;
  }
  return `# ${t('直接在代码中使用环境变量')}
import os
${pythonEnvironment}`;
}

export function buildSandboxExample({ apiUrl, templateId, environmentMode, clientType, t }) {
  const template = templateId || '<templateID>';
  if (clientType === 'http') {
    return `curl --request POST ${shellQuote(`${apiUrl}/sandboxes`)} \\
  --header 'X-API-Key: <your-api-key>' \\
  --header "Content-Type: application/json" \\
  --data-binary @- <<'JSON'
${JSON.stringify({ templateID: template, timeout: 600 }, null, 2)}
JSON`;
  }
  const pythonEnvironment = getPythonEnvironment({ apiUrl, environmentMode });
  const createSandboxCode = getCreateSandboxCode({ templateId, t });
  if (clientType === 'browser') {
    return `import os
import asyncio
from e2b import Sandbox
from playwright.async_api import async_playwright

${pythonEnvironment}

${createSandboxCode}
cdp_url = f"https://{sandbox.get_host(9000)}/cdp"

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(
            cdp_url,
            headers={"X-Access-Token": str(sandbox._envd_access_token)},
        )
        context = browser.contexts[0]
        page = context.pages[0]
        await page.goto("https://example.com")
        await page.wait_for_load_state("networkidle")

asyncio.run(main())`;
  }
  return `import os
from e2b_code_interpreter import Sandbox

${pythonEnvironment}

${createSandboxCode}

# ${t('执行 Python 代码，代码执行超时时间为 600 秒')}
python_code = """
import time
print("hello python")
"""

execution = sandbox.run_code(python_code, timeout=600)
print(execution.logs.stdout)`;
}
