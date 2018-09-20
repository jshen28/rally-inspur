from rally.task import types
from rally.task import validation
from rally_inspur.pepper.cli import PepperExecutor

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.nova import utils
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
                    name="InspurPlugin.nova_conductor_ha",
                    platform="openstack")
class NovaConductorHa(utils.NovaScenario):

    def run(self, image, flavor, salt_passwd=CONF.salt_passwd, salt_api_url=CONF.salt_api_uri, **kwargs):

        # match suffix
        ctl_nodes = [i.host + "*" for i in self.admin_clients("nova").services.list(binary='nova-conductor')]

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        index = 0
        try:
            for node in ctl_nodes:
                LOG.info('stop nova-conductor on node %s' % node)
                index = index + 1
                cmd = [node + '*', 'cmd.run', 'systemctl stop nova-conductor']
                pe.execute(cmd)
                if index == len(ctl_nodes):
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
                LOG.info('restart nova-conductor on node %s' % node)
                try:
                    cmd = [node + '*', 'cmd.run', 'systemctl start nova-conductor']
                    pe.execute(cmd)
                except Exception:
                    pass

            cmp_nodes = [i.host + "*" for i in self.admin_clients("nova").services.list(binary='nova-compute')]
            for node in cmp_nodes:
                LOG.info('restart nova-compute on node %s' % node)
                try:
                    cmd = [node + '*', 'cmd.run', 'systemctl restart nova-compute']
                    pe.execute(cmd)
                except Exception:
                    pass

