# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
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


from rally.common import cfg
from rally.common import logging
from rally.common import validation
from rally.task import context

from rally_openstack import consts

from rally_inspur.pepper.cli import PepperExecutor

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

RESOURCE_MANAGEMENT_WORKERS_DESCR = ("The number of concurrent threads to use "
                                     "for serving users context.")
PROJECT_DOMAIN_DESCR = "ID of domain in which projects will be created."
USER_DOMAIN_DESCR = "ID of domain in which users will be created."


@validation.add("required_platform", platform="openstack", users=True)
@context.configure(name="pepper", platform="openstack", order=120)
class PepperGenerator(context.Context):
    """execute customary pepper command during cleanup and setup"""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "anyOf": [
            {"description": "Create new temporary users and tenants.",
             "properties": {
                "salt_api_url": {
                    "type": "string",
                    "description": "salt api url"
                 },
                 "salt_passwd": {
                     "type": "string",
                     "description": "salt user password"
                 },
                 "execute_at_setup": {
                     "type": "array",
                     "description": "pepper command to be executed during setup"
                 },
                 "execute_at_cleanup": {
                     "type": "array",
                     "description": "pepper command to be executed during cleanup"},
                 },
            "additionalProperties": False}
        ]
    }

    def __init__(self, context):
        super(PepperGenerator, self).__init__(context)
        salt_api_url = self.config['salt_api_url']
        salt_passwd = self.config['salt_passwd']
        self.pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)

    def setup(self):
        cmd = self.config['execute_at_setup']
        for i in self.pe.execute(cmd):
            print(i)

    def cleanup(self):
        cmd = self.config['execute_at_cleanup']
        for i in self.pe.execute(cmd):
            print(i)
