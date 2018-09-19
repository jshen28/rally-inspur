from rally.common import logging
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_openstack.services.image import glance_v2
from rally_openstack.services.image import image
from rally_openstack.scenarios.glance.images import GlanceBasic

from rally_inspur.pepper.cli import PepperExecutor

from abc import abstractmethod

LOG = logging.getLogger(__name__)


class GlanceHa(GlanceBasic):

    def _run(self, salt_api_uri=None, salt_user_passwd=None, binary="glance-api", **kwargs):
        """verify glance service availability

        :param salt_api_uri: salt api uri
        :param salt_user_passwd: salt password
        :param binary:
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)
        hosts = [i.host for i in self.admin_clients('nova').services.list(binary='nova-conductor')]

        index = 1
        try:
            for host in hosts:

                pe.execute([host + "*", 'cmd.run', 'systemctl stop %s' % binary])
                try:
                    self._exec(**kwargs)
                except Exception as e:
                    LOG.error(e)
                    if index < len(hosts):
                        raise Exception('glance-api failed')
        except Exception as e:
            LOG.error(e)
        finally:
            # restore glance-api services
            for host in hosts:
                try:
                    pe.execute([host + "*", 'cmd.run', 'systemctl start %s' % binary])
                except Exception as e:
                    LOG.error(e)

    @abstractmethod
    def _exec(self, **kwargs):
        pass


@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="InspurPlugins.glance_api_ha",
                    platform="openstack")
class GlanceApiHa(GlanceHa):

    def run(self, salt_api_uri=None, salt_user_passwd=None, **kwargs):
        """verify glance api availability

        :param salt_api_uri: salt api uri
        :param salt_user_passwd: salt password
        """
        self._run(salt_api_uri=salt_api_uri, salt_user_passwd=salt_user_passwd)

    def _exec(self, **kwargs):
        self.glance.list_images()


@validation.add("enum", param_name="container_format",
                values=["ami", "ari", "aki", "bare", "ovf"])
@validation.add("enum", param_name="disk_format",
                values=["ami", "ari", "aki", "vhd", "vmdk", "raw",
                        "qcow2", "vdi", "iso"])
@types.convert(image_location={"type": "path_or_url"},
               kwargs={"type": "glance_image_args"})
@validation.add("required_services", services=[consts.Service.GLANCE])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="InspurPlugins.glance_registry_ha",
                    platform="openstack")
class GlanceRegistryHa(GlanceHa):

    def run(self, container_format, image_location, disk_format,
            visibility="private", min_disk=0, min_ram=0, salt_api_uri=None, salt_user_passwd=None, **kwargs):
        """verify glance registry availability

        :param container_format: container format of image. Acceptable
                                formats: ami, ari, aki, bare, and ovf
        :param image_location: image file location
        :param disk_format: disk format of image. Acceptable formats:
                            ami, ari, aki, vhd, vmdk, raw, qcow2, vdi, and iso
        :param visibility: The access permission for the created image
        :param min_disk: The min disk of created images
        :param min_ram: The min ram of created images
        :param salt_api_uri: salt api uri
        :param salt_user_passwd: salt password
        """
        kwargs.update({
            "container_format": container_format,
            "image_location": image_location,
            "disk_format": disk_format,
            "visibility": visibility,
            "min_disk": min_disk,
            "min_ram": min_ram
        })
        self._run(salt_api_uri=salt_api_uri, salt_user_passwd=salt_user_passwd, binary='glance-registry', **kwargs)

    def _exec(self, **kwargs):
        image = self.glance.create_image(
            container_format=kwargs.get('container_format'),
            image_location=kwargs.get('image_location'),
            disk_format=kwargs.get('disk_format'),
            visibility=kwargs.get('visibility'),
            min_disk=kwargs.get('min_disk'),
            min_ram=kwargs.get('min_ram'),
            properties=kwargs.get('properties'))


