#########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
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

import os

from ...exceptions import ProcessExecutionError

from ..validations import validate_certificates
from ..components_constants import (
    SSL_ENABLED,
    SSL_INPUTS,
    SSL_CLIENT_VERIFICATION,
)
from ..base_component import BaseComponent
from ..service_names import POSTGRESQL_CLIENT
from ...constants import (
    POSTGRESQL_CLIENT_CERT_PATH,
    POSTGRESQL_CLIENT_KEY_PATH,
    POSTGRESQL_CA_CERT_PATH,
    CLOUDIFY_HOME_DIR,
    CLOUDIFY_USER,
    CLOUDIFY_GROUP,
    NEW_POSTGRESQL_CA_CERT_FILE_PATH,
    NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH,
    NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH
)
from ...config import config
from ...logger import get_logger
from ...utils import (
    certificates,
    common,
    files,
)

GROUP_USER_ALREADY_EXISTS_EXIT_CODE = 9
POSTGRES_USER = POSTGRES_GROUP = 'postgres'
POSTGRES_USER_ID = POSTGRES_GROUP_ID = '26'
POSTGRES_USER_COMMENT = 'PostgreSQL Server'
POSTGRES_USER_HOME_DIR = '/var/lib/pgsql'
HOST = 'host'

CLOUDIFY_PGPASS_PATH = os.path.join(CLOUDIFY_HOME_DIR, '.pgpass')

PG_PORT = 5432

logger = get_logger(POSTGRESQL_CLIENT)


class PostgresqlClient(BaseComponent):
    def _install(self):
        files.copy_notice(POSTGRESQL_CLIENT)

        db_server_username = config[POSTGRESQL_CLIENT]['server_username']
        if db_server_username == 'postgres' or not db_server_username:
            config[POSTGRESQL_CLIENT]['server_username'] = 'postgres'
            self._create_postgres_group()
            self._create_postgres_user()

    def _create_postgres_group(self):
        logger.notice('Creating postgres group')
        try:
            common.sudo(['groupadd',
                         '-g', POSTGRES_GROUP_ID,
                         '-o', '-r',
                         POSTGRES_GROUP])
        except ProcessExecutionError as ex:
            # Return code 9 for non-unique user/group
            if ex.return_code != GROUP_USER_ALREADY_EXISTS_EXIT_CODE:
                raise ex
            else:
                logger.info('Group postgres already exists')

    def _create_postgres_user(self):
        logger.notice('Creating postgres user')
        try:
            # In case All-in-one, the user already exists so the home dir
            # won't be created.
            common.sudo(['useradd', '-m', '-N',
                         '-g', POSTGRES_GROUP_ID,
                         '-o', '-r',
                         '-d', POSTGRES_USER_HOME_DIR,
                         '-s', '/bin/bash',
                         '-c', POSTGRES_USER_COMMENT,
                         '-u', POSTGRES_USER_ID, POSTGRES_USER])
        except ProcessExecutionError as ex:
            # Return code 9 for non-unique user/group
            if ex.return_code != GROUP_USER_ALREADY_EXISTS_EXIT_CODE:
                raise ex
            else:
                logger.info('User postgres already exists')

    def _create_pgpass(self, host, port, db_name, user, password, pgpass_path,
                       owning_user, owning_group):
        logger.debug('Creating postgresql pgpass file: {0}'
                     .format(pgpass_path))
        pgpass_content = '{host}:{port}:{db_name}:{user}:{password}'.format(
            host=host,
            port=port,
            db_name=db_name,
            user=user,
            password=password
        )
        files.write_to_file(pgpass_content, pgpass_path)
        common.chmod('400', pgpass_path)
        common.chown(owning_user, owning_group, pgpass_path)

        logger.debug('Postgresql pass file {0} created'.format(pgpass_path))

    def _create_postgres_pgpass_files(self):
        pg_config = config[POSTGRESQL_CLIENT]
        host = pg_config['host']
        port = PG_PORT

        # Creating Cloudify .pgpass file
        db_name = '*'  # Allowing for the multiple DBs we have
        user = pg_config['cloudify_username']
        password = pg_config['cloudify_password']
        self._create_pgpass(
            host=host,
            port=port,
            db_name=db_name,
            user=user,
            password=password,
            pgpass_path=CLOUDIFY_PGPASS_PATH,
            owning_user=CLOUDIFY_USER,
            owning_group=CLOUDIFY_GROUP
        )

    def _configure_ssl(self):
        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            self._handle_ca_certificate()

            if config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION]:
                self._handle_cert_and_key()

    def _handle_ca_certificate(self):
        certificates.use_supplied_certificates(
            logger=self.logger,
            ca_destination=POSTGRESQL_CA_CERT_PATH,
            component_name=POSTGRESQL_CLIENT
        )

    def _handle_cert_and_key(self):
        certificates.use_supplied_certificates(
            logger=self.logger,
            cert_destination=POSTGRESQL_CLIENT_CERT_PATH,
            key_destination=POSTGRESQL_CLIENT_KEY_PATH,
            key_perms='400',
            component_name=SSL_INPUTS,
            prefix='postgresql_client_'
        )

    def replace_certificates(self):
        replacing_ca = os.path.exists(NEW_POSTGRESQL_CA_CERT_FILE_PATH)
        replacing_cert_and_key = os.path.exists(
            NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH)
        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            self.validate_new_certs()
            if replacing_ca:
                self.logger.info(
                    'Replacing CA cert on postgresql_client component')
                config[POSTGRESQL_CLIENT]['ca_path'] = \
                    NEW_POSTGRESQL_CA_CERT_FILE_PATH
                self._handle_ca_certificate()
            if (config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION] and
                    replacing_cert_and_key):
                self.logger.info(
                    'Replacing cert and key on postgresql_client component')
                config[SSL_INPUTS]['postgresql_client_cert_path'] = \
                    NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH
                config[SSL_INPUTS]['postgresql_client_key_path'] = \
                    NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH
                self._handle_cert_and_key()

    def validate_new_certs(self):
        if config[POSTGRESQL_CLIENT][SSL_ENABLED]:
            cert_filename, key_filename = None, None
            if config[POSTGRESQL_CLIENT][SSL_CLIENT_VERIFICATION]:
                cert_filename, key_filename = \
                    certificates.get_cert_and_key_filenames(
                        NEW_POSTGRESQL_CLIENT_CERT_FILE_PATH,
                        NEW_POSTGRESQL_CLIENT_KEY_FILE_PATH,
                        POSTGRESQL_CLIENT_CERT_PATH,
                        POSTGRESQL_CLIENT_KEY_PATH)

            ca_filename = certificates.get_ca_filename(
                NEW_POSTGRESQL_CA_CERT_FILE_PATH,
                POSTGRESQL_CA_CERT_PATH)

            validate_certificates(cert_filename, key_filename, ca_filename)

    def _configure(self):
        self._create_postgres_pgpass_files()
        self._configure_ssl()

    def install(self):
        logger.notice('Installing PostgreSQL Client...')
        self._install()
        logger.notice('PostgreSQL successfully installed')

    def configure(self):
        logger.notice('Configuring PostgreSQL Client...')
        self._configure()
        logger.notice('PostgreSQL successfully configured')

    def remove(self):
        files.remove_notice(POSTGRESQL_CLIENT)
