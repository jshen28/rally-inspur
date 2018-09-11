# Copyright 2013: Mirantis Inc.
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

from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils

from rally_inspur.pepper.cli import PepperExecutor


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="SjtPlugin.boot_server",
                    platform="openstack")
class BootServer(utils.NovaScenario):

    def run(self, image, flavor, auto_assign_nic=False, salt_passwd=None, salt_api_url=None, execute_before=list(), execute_after=list(), **kwargs):
        """Boot a server.

        Assumes that cleanup is done elsewhere.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param auto_assign_nic: True if NICs should be assigned
        :param salt_passwd: salt user password
        :param salt_api_url: salt api url
        :param cmd: cmds to be executed by salt
        :param kwargs: Optional additional arguments for server creation
        """

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        pe.execute(execute_before)

        try:
            self._boot_server(image, flavor,
                              auto_assign_nic=auto_assign_nic, **kwargs)
        pe.execute(execute_after)