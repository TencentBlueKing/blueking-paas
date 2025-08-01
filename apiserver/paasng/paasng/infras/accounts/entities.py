#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from typing import List

from attrs import define


@define
class OauthCredential:
    """OAuth 授权凭证

    :param oauth_token: OAuth 授权凭证
    :param scope_list: OAuth 授权范围
    """

    oauth_token: str
    scope_list: List
