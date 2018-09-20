# Copyright 2013 Huawei Technologies Co.,LTD.
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
from rally.common import logging, opts
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_inspur.pepper.cli import PepperExecutor


CONF = opts.CONF
LOG = logging.getLogger(__name__)


class CinderVolumeHaDeprecated(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """Create a volume and list all volumes.

        Measure the "cinder volume-list" command performance.

        If you have only 1 user in your context, you will
        add 1 volume on every iteration. So you will have more
        and more volumes and will be able to measure the
        performance of the "cinder volume-list" command depending on
        the number of images owned by users.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume
        :param salt_api_url
        :param salt_user_passwd
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_user_passwd)

        hosts = [i.host.split('@')[0] for i in self._admin_clients.cinder.create_client()
            .services.list(binary='cinder-volume')]

        try:
            index = 0
            for host in hosts:
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-volume'])
                try:
                    self.cinder.create_volume(size, **kwargs)
                except Exception as e:
                    LOG.error(e)
                    if index != len(hosts):
                        raise e

        except Exception as e:
            LOG.error(e)
        finally:
            for host in hosts:
                if host.state != 'up':
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-volume'])


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("restricted_parameters", param_names=["name", "display_name"],
                subdict="create_volume_params")
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA,
                                               consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder", "nova"]},
                    name="InspurPlugin.cinder_volume_ha",
                    platform="openstack")
class CreateAndAttachVolume(cinder_utils.CinderBasic,
                            nova_utils.NovaScenario):

    @logging.log_deprecated_args(
        "Use 'create_vm_params' for additional instance parameters.",
        "0.2.0", ["kwargs"], once=True)
    def run(self, size, image, flavor, create_volume_params=None,
            create_vm_params=None, salt_api_url=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """Create a VM and attach a volume to it.

        Simple test to create a VM and attach a volume, then
        detach the volume and delete volume/VM.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: Glance image name to use for the VM
        :param flavor: VM flavor name
        :param create_volume_params: optional arguments for volume creation
        :param create_vm_params: optional arguments for VM creation
        :param salt_api_url
        :param salt_user_passwd
        :param kwargs: (deprecated) optional arguments for VM creation
        """

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_user_passwd)

        hosts = [i.host.split('@')[0] for i in self._admin_clients.cinder.create_client()
            .services.list(binary='cinder-volume')]

        create_volume_params = create_volume_params or {}

        if kwargs and create_vm_params:
            raise ValueError("You can not set both 'kwargs'"
                             "and 'create_vm_params' attributes."
                             "Please use 'create_vm_params'.")

        create_vm_params = create_vm_params or kwargs or {}

        server = self._boot_server(image, flavor, **create_vm_params)
        volume = self.cinder.create_volume(size, **create_volume_params)

        index = 0
        try:
            for host in hosts:
                LOG.info('stop cinder-volume on %s ' % host)
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-volume'])
                self._attach_volume(server, volume)
                self._detach_volume(server, volume)
        except Exception as e:
            LOG.error(e)
            if index != len(hosts):
                raise e
        finally:
            for host in hosts:
                LOG.info('start cinder-volume on %s ' % host)
                if host.state != 'up':
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-volume'])

            import time
            LOG.info('waiting for 15s before resuming')
            time.sleep(15)

            self._attach_volume(server, volume)
            self._detach_volume(server, volume)
            self.cinder.delete_volume(volume)
            self._delete_server(server)


@types.convert(image={"type": "glance_image"})
@validation.add("image_exists", param_name="image", nullable=True)
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder"]},
                    name="InspurPlugin.cinder_scheduler_ha",
                    platform="openstack")
class CinderSchedulerHa(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """Create a volume and list all volumes.

        Measure the "cinder volume-list" command performance.

        If you have only 1 user in your context, you will
        add 1 volume on every iteration. So you will have more
        and more volumes and will be able to measure the
        performance of the "cinder volume-list" command depending on
        the number of images owned by users.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume
        :param salt_api_url
        :param salt_user_passwd
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_user_passwd)

        hosts = [i.host for i in self._admin_clients.cinder.create_client()
            .services.list(binary='cinder-scheduler')]

        index = 0
        try:
            for host in hosts:
                LOG.info('stop cinder-scheduler on node %s' % host)
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-scheduler'])
                self.cinder.create_volume(size, **kwargs)
        except Exception as e:
            LOG.error(e)
            if index != len(hosts):
                raise e
        finally:
            for host in hosts:
                LOG.info('start cinder-scheduler on %s' % host)
                try:
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-scheduler'])
                except Exception as e:
                    LOG.error(e)


@types.convert(image={"type": "glance_image"})
@validation.add("image_exists", param_name="image", nullable=True)
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder"]},
                    name="InspurPlugin.cinder_api_ha",
                    platform="openstack")
class CinderApiHa(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """Create a volume and list all volumes.

        Measure the "cinder volume-list" command performance.

        If you have only 1 user in your context, you will
        add 1 volume on every iteration. So you will have more
        and more volumes and will be able to measure the
        performance of the "cinder volume-list" command depending on
        the number of images owned by users.

        :param size: volume size (integer, in GB) or
                     dictionary, must contain two values:
                         min - minimum size volumes will be created as;
                         max - maximum size volumes will be created as.
        :param image: image to be used to create volume
        :param salt_api_url
        :param salt_user_passwd
        :param kwargs: optional args to create a volume
        """
        if image:
            kwargs["imageRef"] = image

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_user_passwd)

        hosts = [i.host for i in self.admin_cinder.services.list(binary='cinder-scheduler')]

        try:
            index = 0
            for host in hosts:
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-api'])
                try:
                    self.cinder.create_volume(size, **kwargs)
                except Exception as e:
                    LOG.error(e)
                    if index != len(hosts):
                        raise e
        finally:
            for host in hosts:
                LOG.info('start cinder-api on %s' % host)
                try:
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-api'])
                except Exception as e:
                    LOG.error(e)

