#########
# Copyright (c) 2018-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

import json
import argh
from os.path import join

from ..logger import get_logger, setup_console_logger
from ..constants import (
    NETWORKS_DIR,
)
from ..utils.certificates import (
    create_internal_certs,
    load_cert_metadata,
    store_cert_metadata
)
from ..utils.scripts import run_script_on_manager_venv

SCRIPT_DIR = join(NETWORKS_DIR, 'scripts')
REST_HOME_DIR = '/opt/manager'

logger = get_logger('networks')


def _validate_duplicate_network(old_networks, new_networks):
    """Check that all networks have unique names"""
    for network in new_networks:
        if network in old_networks:
            raise Exception('Network name {0} already exists. Cannot add '
                            'new networks. Choose uniqe network names and '
                            'run the command again'.format(network))


def _update_metadata_file(metadata, networks):
    """
    Add the new networks to /etc/cloudify/ssl/certificate_metadata
    :param networks: a dict containing the new networks
    """

    old_networks = metadata['network_names']
    new_networks = list(networks.keys())
    _validate_duplicate_network(old_networks, new_networks)
    if metadata.get('broker_addresses'):
        new_brokers = list(networks.values())
    else:
        new_brokers = None
    if metadata.get('manager_addresses'):
        new_managers = list(networks.values())
    else:
        new_managers = None

    store_cert_metadata(
        new_networks=list(networks.keys()),
        new_brokers=new_brokers,
        new_managers=new_managers,
    )


@argh.arg('--networks',
          help='A JSON string containing the new networks to be added to the'
               ' Manager. Example: \'{"<network-name>": "<ip>"}\'',
          required=True)
@argh.arg('--skip-generating-certificates',
          help='Specify whether we skip generating certificates, so the user '
               'can provide their own, e.g. signed by a public CA',
          default=False)
def add_networks(networks=None,
                 skip_generating_certificates=False,
                 verbose=False):
    """
    Add new networks to a running Cloudify Manager
    """
    setup_console_logger(verbose)
    logger.info('Trying to add new networks to Manager...')

    networks = json.loads(networks)
    metadata = load_cert_metadata()

    _update_metadata_file(metadata, networks)
    if not skip_generating_certificates:
        create_internal_certs()

    script_path = join(SCRIPT_DIR, 'update-manager-networks.py')
    args = [
        '--hostname', metadata['hostname'],
        '--networks', json.dumps(networks),
    ]
    if bool(metadata.get('broker_addresses')):
        # if we store broker addresses in the metadata file, that means we
        # have a local broker and must update that too
        args.append('--broker')

    run_script_on_manager_venv(script_path, script_args=args)

    logger.notice('New networks were added successfully. Please restart the'
                  ' following services: `nginx`, `cloudify-mgmtworker`,'
                  '`cloudify-rabbitmq`')
