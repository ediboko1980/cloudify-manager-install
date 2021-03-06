#########
# Copyright (c) 2019 Cloudify Platform Ltd. All rights reserved
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
import time
import uuid
from os.path import join

from .manager_config import make_manager_config
from ..components_constants import (
    AGENT,
    SCRIPTS,
    HOSTNAME,
    SECURITY,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    PROVIDER_CONTEXT,
    SERVICES_TO_INSTALL,
)

from ..service_names import (
    MANAGER,
    POSTGRESQL_CLIENT,
    POSTGRESQL_SERVER,
    RABBITMQ,
    RESTSERVICE,
    DATABASE_SERVICE
)

from ... import constants
from ...config import config
from ...logger import get_logger
from ...exceptions import ValidationError

from ...utils import common, db as utils_db
from ...utils.install import is_premium_installed
from ...utils.files import temp_copy
from ...utils.scripts import run_script_on_manager_venv

logger = get_logger('DB')

SCRIPTS_PATH = join(constants.COMPONENTS_DIR, RESTSERVICE, SCRIPTS)
REST_HOME_DIR = '/opt/manager'
NETWORKS = 'networks'
UUID4HEX_LEN = 32
ENCODED_USER_ID_LENGTH = 5


def drop_db():
    logger.notice('PREPARING TO DROP CLOUDIFY DATABASE...')
    logger.notice(
        'You have 10 seconds to press Ctrl+C if this was a mistake.'
    )
    time.sleep(10)
    _execute_db_script('drop_db.sh')
    logger.info('Cloudify database successfully dropped.')


def prepare_db():
    logger.notice('Configuring SQL DB...')
    _execute_db_script('create_default_db.sh')
    logger.notice('SQL DB successfully configured')


def _execute_db_script(script_name):
    pg_config = config[POSTGRESQL_CLIENT]

    script_path = join(SCRIPTS_PATH, script_name)
    tmp_script_path = temp_copy(script_path)
    common.chmod('o+rx', tmp_script_path)
    username = pg_config['cloudify_username'].split('@')[0]
    db_script_command = \
        '{cmd} {db} {user} {password}'.format(
            cmd=tmp_script_path,
            db=pg_config['cloudify_db_name'],
            user=username,
            password=pg_config['cloudify_password']
        )

    if DATABASE_SERVICE in config[SERVICES_TO_INSTALL]:
        # In case the default user is postgres and we're in AIO installation,
        # "peer" authentication is used
        if config[POSTGRESQL_CLIENT]['server_username'] == 'postgres':
            db_script_command = '-u postgres ' + db_script_command

    db_env = utils_db.generate_db_env(database=pg_config['server_db_name'])

    common.sudo(db_script_command, env=db_env)


def _get_provider_context():
    context = {'cloudify': config[PROVIDER_CONTEXT]}
    context['cloudify']['cloudify_agent'] = config[AGENT]
    return context


def _create_populate_db_args_dict():
    """
    Create and return a dictionary with all the information necessary for the
    script that creates and populates the DB to run
    """
    args_dict = {
        'admin_username': config[MANAGER][SECURITY][ADMIN_USERNAME],
        'admin_password': config[MANAGER][SECURITY][ADMIN_PASSWORD],
        'provider_context': _get_provider_context(),
        'authorization_file_path': join(REST_HOME_DIR, 'authorization.conf'),
        'db_migrate_dir': join(constants.MANAGER_RESOURCES_HOME, 'cloudify',
                               'migrations'),
        'config': make_manager_config(),
        'premium': 'premium' if is_premium_installed() else 'community',
        'rabbitmq_brokers': _create_rabbitmq_info(),
        'db_nodes': _create_db_nodes_info(),
        'usage_collector': _create_usage_collector_info()
    }
    rabbitmq_ca_cert_path = config['rabbitmq'].get('ca_path')
    if rabbitmq_ca_cert_path:
        with open(rabbitmq_ca_cert_path) as f:
            args_dict['rabbitmq_ca_cert'] = f.read()
    return args_dict


def _create_rabbitmq_info():
    monitoring_username = config[RABBITMQ].get(
        'monitoring', {}).get('username')
    monitoring_password = config[RABBITMQ].get(
        'monitoring', {}).get('password')
    if not monitoring_username or not monitoring_password:
        monitoring_username = config[RABBITMQ].get('username')
        monitoring_password = config[RABBITMQ].get('password')

    return [
        {
            'name': name,
            'host': broker[NETWORKS]['default'],
            'management_host': (
                '127.0.0.1' if config[RABBITMQ]['management_only_local']
                else broker[NETWORKS]['default']
            ),
            'username': config[RABBITMQ]['username'],
            'password': config[RABBITMQ]['password'],
            'params': None,
            'networks': broker[NETWORKS],
            'is_external': broker.get('networks', {}).get('default') is None,
            'monitoring_username': monitoring_username,
            'monitoring_password': monitoring_password,
        }
        for name, broker in config[RABBITMQ]['cluster_members'].items()
    ]


def _create_db_nodes_info():
    monitoring_username = config[POSTGRESQL_CLIENT].get(
        'monitoring', {}).get('username')
    monitoring_password = config[POSTGRESQL_CLIENT].get(
        'monitoring', {}).get('password')
    if not monitoring_username or not monitoring_password:
        monitoring_username = config[POSTGRESQL_CLIENT].get('server_username')
        monitoring_password = config[POSTGRESQL_CLIENT].get('server_password')

    if common.is_all_in_one_manager():
        return [{
            'name': config[MANAGER][HOSTNAME],
            'host': config[NETWORKS]['default'],
            'is_external': False,
            'monitoring_username': monitoring_username,
            'monitoring_password': monitoring_password,
        }]

    if common.manager_using_db_cluster():
        db_nodes = config[POSTGRESQL_SERVER]['cluster']['nodes']
        return [
            {
                'name': name,
                'host': db['ip'],
                'is_external': False,
                'monitoring_username': monitoring_username,
                'monitoring_password': monitoring_password,
            }
            for name, db in db_nodes.items()
        ]

    # External db is used
    return [{
        'name': config[POSTGRESQL_CLIENT]['host'],
        'host': config[POSTGRESQL_CLIENT]['host'],
        'is_external': True,
        'monitoring_username': monitoring_username,
        'monitoring_password': monitoring_password,
    }]


def _create_usage_collector_info():
    cfy_uptime = config['usage_collector']['collect_cloudify_uptime']
    cfy_usage = config['usage_collector']['collect_cloudify_usage']
    return {
        'id': 0,
        'manager_id': uuid.uuid4().hex,
        'hourly_timestamp': None,
        'daily_timestamp': None,
        'hours_interval': cfy_uptime['interval_in_hours'],
        'days_interval': cfy_usage['interval_in_days']
    }


def _create_process_env(rest_config=None, authorization_config=None,
                        security_config=None):
    env = {}
    for value, envvar in [
            (rest_config, 'MANAGER_REST_CONFIG_PATH'),
            (security_config, 'MANAGER_REST_SECURITY_CONFIG_PATH'),
            (authorization_config, 'MANAGER_REST_AUTHORIZATION_CONFIG_PATH'),
    ]:
        if value is not None:
            env[envvar] = value
    return env


def run_script(script_name, script_input=None, configs=None):
    """Runs a script in a separate process.

    :param script_name: script name inside the SCRIPTS_PATH dir.
    :param script_input: script input to pass to the script.
    :param configs: keword arguments dict to pass to _create_process_env(..).
    :return: the script's returned when it finished its execution.
    """
    env_dict = _create_process_env(**configs) if configs else None

    script_path = join(SCRIPTS_PATH, script_name)

    proc_result = run_script_on_manager_venv(script_path,
                                             script_input,
                                             envvars=env_dict)
    return _get_script_stdout(proc_result)


def populate_db(configs):
    logger.notice('Populating DB and creating AMQP resources...')
    args_dict = _create_populate_db_args_dict()
    run_script('create_tables_and_add_defaults.py', args_dict, configs)
    logger.notice('DB populated and AMQP resources successfully created')


def insert_manager(configs):
    logger.notice('Registering manager in the DB...')
    monitoring_username = config['manager'].get(
        'monitoring', {}).get('username')
    monitoring_password = config['manager'].get(
        'monitoring', {}).get('password')
    if not monitoring_username or not monitoring_password:
        monitoring_username = config['manager']['security']['admin_username']
        monitoring_password = config['manager']['security']['admin_password']
    args = {
        'manager': {
            'public_ip': config['manager']['public_ip'],
            'hostname': config[MANAGER][HOSTNAME],
            'private_ip': config['manager']['private_ip'],
            'networks': config[NETWORKS],
            'last_seen': common.get_formatted_timestamp(),
            'monitoring_username': monitoring_username,
            'monitoring_password': monitoring_password,
        }
    }

    try:
        with open(constants.CA_CERT_PATH) as f:
            args['manager']['ca_cert'] = f.read()
    except IOError:
        args['manager']['ca_cert'] = None
    out = run_script('create_tables_and_add_defaults.py', args, configs)
    if out:
        out_dict = json.loads(out)
        if 'cluster_nodes_config' in out_dict:
            return (out_dict.get('cluster_nodes_config'),
                    out_dict.get('rabbitmq_ca_cert_path'),)


def create_amqp_resources(configs=None):
    logger.notice('Creating AMQP resources...')
    run_script('create_amqp_resources.py', configs=configs)
    logger.notice('AMQP resources successfully created')


def check_db_exists():
    # Get the list of databases
    result = utils_db.run_psql_command(
        command=['-l'],
        db_key='server_db_name',
    )

    # Example of expected output:
    # cloudify_db | cloudify | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =Tc/cloudify         +  # noqa
    #             |          |          |             |             | cloudify=CTc/cloudify   # noqa
    # composer    | cloudify | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =Tc/cloudify         +  # noqa
    #             |          |          |             |             | cloudify=CTc/cloudify   # noqa
    # postgres    | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 |                         # noqa
    # stage       | cloudify | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =Tc/cloudify         +  # noqa
    #             |          |          |             |             | cloudify=CTc/cloudify   # noqa
    # template0   | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +  # noqa
    #             |          |          |             |             | postgres=CTc/postgres   # noqa
    # template1   | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +  # noqa
    #             |          |          |             |             | postgres=CTc/postgres   # noqa
    #                                                                                         # noqa

    result = result.splitlines()
    dbs = [db.split('|')[0].strip() for db in result]
    dbs = [db for db in dbs if db]  # Clear out empty strings

    return config[POSTGRESQL_CLIENT]['cloudify_db_name'] in dbs


def manager_is_in_db():
    result = utils_db.run_psql_command(
        command=[
            '-c', "SELECT COUNT(*) FROM managers where hostname='{0}'".format(
                config[MANAGER][HOSTNAME],
            ),
        ],
        db_key='cloudify_db_name',
    )

    # As the name is unique, there can only ever be at most 1 entry with the
    # expected name, and if there is then the manager is in the db.
    return int(result) == 1


def validate_schema_version(configs):
    """Check that the database schema version is the same as the current
    manager's migrations version.
    """
    migrations_version = run_script('get_db_version.py', configs=configs)
    db_version = utils_db.run_psql_command(
        command=['-c', 'SELECT version_num FROM alembic_version'],
        db_key='cloudify_db_name'
    )
    migrations_version = migrations_version.strip()
    db_version = db_version.strip()
    if migrations_version != db_version:
        raise ValidationError(
            'Database schema version mismatch: this manager expects schema '
            'revision {0} but the database is {1})'
            .format(migrations_version, db_version))


def _get_script_stdout(result):
    """Log stderr output from the script and return the return stdout from the
    script.
    :param result: Popen result.
    """
    if result.aggr_stderr:
        output = result.aggr_stderr.split('\n')
        output = [line.strip() for line in output if line.strip()]
        for line in output:
            logger.debug(line)
    return result.aggr_stdout if result.aggr_stdout else ""
