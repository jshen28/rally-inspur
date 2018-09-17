from rally.task import types
from rally.task import validation
from rally_inspur.pepper.cli import PepperExecutor

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils
from oslo_log import log

LOG = log.getLogger(__name__)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.nova_conductor_ha",
                    platform="openstack")
class NovaConductorHa(utils.NovaScenario):

    def run(self, image, flavor, salt_passwd=None, salt_api_url=None, **kwargs):

        # match suffix
        ctl_nodes = [i.host + "*" for i in self.admin_clients("nova").services.list(binary='nova-conductor')]

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        index = 0
        try:
            for node in ctl_nodes:
                cmd = [node, 'cmd.run', 'systemctl stop nova-conductor']
                pe.execute(cmd)
                if index == (len(ctl_nodes) - 1):
                    try:
                        self._boot_server(image, flavor, **kwargs)
                    except Exception as e:
                        LOG.debug(e)
                else:
                    self._boot_server(image, flavor, **kwargs)

        except Exception as e:
            LOG.error(e)
            raise
        finally:
            for node in ctl_nodes:
                try:
                    cmd = [node, 'cmd.run', 'systemctl start nova-conductor']
                    pe.execute(cmd)
                except Exception:
                    pass

