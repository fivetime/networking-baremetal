#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from keystoneauth1 import loading
import openstack
from oslo_config import cfg
from oslo_log import log as logging
import tenacity

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

_IRONIC_SESSION = None
IRONIC_GROUP = 'ironic'


def list_opts():
    return [
        (IRONIC_GROUP,
         loading.get_adapter_conf_options()
         + loading.get_session_conf_options()
         + loading.get_auth_plugin_conf_options('v3password'))]


def get_session(group):
    loading.register_adapter_conf_options(CONF, group)
    loading.register_session_conf_options(CONF, group)
    loading.register_auth_conf_options(CONF, group)
    auth = loading.load_auth_from_conf_options(CONF, group)
    session = loading.load_session_from_conf_options(CONF, group, auth=auth)
    return session


def _get_ironic_session():
    global _IRONIC_SESSION

    if not _IRONIC_SESSION:
        _IRONIC_SESSION = get_session(IRONIC_GROUP)
    return _IRONIC_SESSION


@tenacity.retry(
    retry=tenacity.retry_if_exception_type(openstack.exceptions.NotSupported),
    wait=tenacity.wait_exponential(max=30))
def get_client():
    """Get an ironic client connection."""
    session = _get_ironic_session()

    try:
        return openstack.connection.Connection(
            session=session, oslo_conf=CONF).baremetal
    except openstack.exceptions.NotSupported as exc:
        LOG.error('Ironic API might not be running, failed to establish a '
                  'connection with ironic, reason: %s. Retrying ...', exc)
        raise
    except Exception as exc:
        LOG.error('Failed to establish a connection with ironic, reason: %s',
                  exc)
        raise
