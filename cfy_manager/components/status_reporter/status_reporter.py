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

import uuid

from ..base_component import BaseComponent

from ...logger import get_logger
from ...components import sources
from ...utils import service
from ...utils.files import update_yaml_file
from ...utils.install import yum_install, yum_remove
from ...utils.files import (remove_files,
                            check_rpms_are_present)
from ...constants import (STATUS_REPORTER,
                          STATUS_REPORTER_PATH,
                          STATUS_REPORTER_CONFIGURATION_PATH)

logger = get_logger(STATUS_REPORTER)


class StatusReporter(BaseComponent):
    def __init__(self, skip_installation, reporter_type):
        skip_installation = (skip_installation or
                             not check_rpms_are_present(
                                 sources.status_reporter))
        super(StatusReporter, self).__init__(skip_installation)
        self.reporter_type = reporter_type

    def _build_extra_config_flags(self):
        return ''

    def install(self):
        logger.notice('Installing Status Reporter {0}...'.format(
            self.reporter_type))
        yum_install(sources.status_reporter)
        logger.notice('Status Reporter {0} successfully installed'.format(
            self.reporter_type))

    def configure(self):
        logger.notice('Configuring status reporter {0}...'.format(
            self.reporter_type))
        reporter_settings = {'reporter_type': self.reporter_type,
                             'extra_config_flags':
                                 self._build_extra_config_flags()}
        service.configure(STATUS_REPORTER,
                          external_configure_params=reporter_settings)
        logger.notice('Generating node id...')
        node_id = self._generate_node_id()
        logger.notice('Generated "{0}" node id.'.format(node_id))
        logger.notice('Status reporter {0} successfully configured'.format(
            self.reporter_type))

    @staticmethod
    def _generate_node_id():
        node_id = str(uuid.uuid4())
        update_yaml_file(STATUS_REPORTER_CONFIGURATION_PATH,
                         'cfyreporter',
                         'cfyreporter',
                         {'node_id': node_id})
        return node_id

    def remove(self):
        logger.notice('Removing status reporter {0}...'.format(
            self.reporter_type))
        service.remove(STATUS_REPORTER)
        yum_remove('cloudify-status-reporter')
        logger.info('Removing status reporter directory...')
        remove_files([STATUS_REPORTER_PATH])
        logger.notice('Status reporter {0} successfully removed'.format(
            self.reporter_type))
