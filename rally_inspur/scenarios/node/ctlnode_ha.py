from rally_inspur.scenarios.utils.basic_ha import BasicNovaHa
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_inspur.pepper.cli import PepperExecutor
from rally.common import logging, opts

LOG = logging.getLogger(__name__)
CONF = opts.CONF


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.controller_node_ha",
                    platform="openstack")
class ControllerNodeHa(BasicNovaHa):

    def run(self, image, flavor, hosts=list(['kvm01', 'kvm02', 'kvm03']),
            salt_passwd=CONF.salt_passwd, salt_api_uri=CONF.salt_api_uri, **kwargs):
        kwargs.update({
            "image": image,
            "flavor": flavor
        })
        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_passwd)
        hosts = hosts or [i.host for i in self.admin_clients('nova').services.list(binary='nova-conductor')]
        index = 1
        try:
            for host in sorted(hosts):
                index = index + 1
                pe.execute([host + "*", 'cmd.run',
                            "virsh list | grep -P 'ctl[0-9]{1,}' | awk '{print $2}' | xargs virsh destroy"])
                try:
                    self._exec(**kwargs)
                except Exception as e:
                    LOG.error(e)
                    if index < len(hosts):
                        raise Exception('accessing services failed!')
        finally:

            for host in sorted(hosts, reverse=True):
                try:
                    pe.execute([host + "*", 'cmd.run',
                                "virsh list --all | grep -P 'ctl[0-9]{1,}' | awk '{print $2}' | xargs virsh start"])
                except Exception as e:
                    LOG.error(e)
                    pass