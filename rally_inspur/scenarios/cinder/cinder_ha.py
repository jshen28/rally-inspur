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
from rally.common import logging
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_inspur.pepper.cli import PepperExecutor


LOG = logging.getLogger(__name__)


@types.convert(image={"type": "glance_image"})
@validation.add("image_exists", param_name="image", nullable=True)
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder"]},
                    name="InspurPlugins.cinder_volume_ha",
                    platform="openstack")
class CinderVolumeHa(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=None, salt_user_passwd=None, **kwargs):
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

        hosts = [i.host.split('@')[0] for i in self.admin_cinder.services.list(binary='cinder-volume')]

        try:
            index = 1
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


@types.convert(image={"type": "glance_image"})
@validation.add("image_exists", param_name="image", nullable=True)
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder"]},
                    name="InspurPlugins.cinder_scheduler_ha",
                    platform="openstack")
class CinderSchedulerHa(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=None, salt_user_passwd=None, **kwargs):
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
            index = 1
            for host in hosts:
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-scheduler'])
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
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-scheduler'])


@types.convert(image={"type": "glance_image"})
@validation.add("image_exists", param_name="image", nullable=True)
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["cinder"]},
                    name="InspurPlugins.cinder_api_ha",
                    platform="openstack")
class CinderApiHa(cinder_utils.CinderBasic):

    def run(self, size, image=None, salt_api_url=None, salt_user_passwd=None, **kwargs):
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
            index = 1
            for host in hosts:
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop cinder-api'])
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
                    pe.execute([host + '*', 'cmd.run', 'systemctl start cinder-api'])

