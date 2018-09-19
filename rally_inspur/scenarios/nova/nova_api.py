
from rally.task import types
from rally.task import validation
from rally.common import logging, opts

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils

from rally_inspur.pepper.cli import PepperExecutor

LOG = logging.getLogger(__name__)
CONF = opts.CONF


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.nova_api_ha",
                    platform="openstack")
class NovaApiHa(utils.NovaScenario):

    def run(self, image, flavor, auto_assign_nic=False,
            salt_passwd=CONF.salt_passwd, salt_api_url=CONF.salt_api_uri, ctl_nodes=list(), **kwargs):

        # Get number of all clt nodes
        conductor_services = self.admin_clients("nova").services.list(binary='nova-conductor')
        if len(ctl_nodes) < len(conductor_services):
            print('This test case needs all ctl nodes')
            return

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        index = 0
        try:
            for node in ctl_nodes:
                cmd = [node, 'cmd.run', 'systemctl stop nova-api']
                pe.execute(cmd)
                if index == (len(ctl_nodes) - 1):
                    self._boot_server_error(image, flavor,
                                            auto_assign_nic=auto_assign_nic, **kwargs)
                else:
                    self._boot_server(image, flavor,
                                      auto_assign_nic=auto_assign_nic, **kwargs)

        except Exception as e:
            print(e)
            raise
        finally:
            for node in ctl_nodes:
                cmd = [node, 'cmd.run', 'systemctl start nova-api']
                pe.execute(cmd)

    def _boot_server_error(self, image, flavor,
                           auto_assign_nic=False, **kwargs):
        server_name = self.generate_random_name()
        secgroup = self.context.get("user", {}).get("secgroup")
        if secgroup:
            if "security_groups" not in kwargs:
                kwargs["security_groups"] = [secgroup["name"]]
            elif secgroup["name"] not in kwargs["security_groups"]:
                kwargs["security_groups"].append(secgroup["name"])

        if auto_assign_nic and not kwargs.get("nics", False):
            nic = self._pick_random_nic()
            if nic:
                kwargs["nics"] = nic

        try:
            server = self.clients("nova").servers.create(
                server_name, image, flavor, **kwargs)
        except Exception as e:
            print(e)
