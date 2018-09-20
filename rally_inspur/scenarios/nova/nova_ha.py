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
                    name="InspurPlugin.nova_scheduler_ha",
                    platform="openstack")
class NovaSchedulerHa(utils.NovaScenario):

    def run(self, image, flavor, salt_passwd=CONF.salt_passwd, salt_api_url=CONF.salt_api_uri, **kwargs):

        # match suffix
        ctl_nodes = [i.host + "*" for i in self.admin_clients("nova").services.list(binary='nova-scheduler')]

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        index = 0
        try:
            for node in ctl_nodes:
                LOG.info('stop nova-scheduler on node %s' % node)
                index = index + 1
                cmd = [node, 'cmd.run', 'systemctl stop nova-scheduler']
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
                LOG.info('restart noova-scheduler on node %s' % node)
                try:
                    cmd = [node, 'cmd.run', 'systemctl start nova-scheduler']
                    pe.execute(cmd)
                except Exception:
                    pass


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.nova_consoleauth_ha",
                    platform="openstack")
class NovaConsoleauthHa(utils.NovaScenario):

    def run(self, image, flavor, salt_passwd=CONF.salt_passwd, salt_api_url=CONF.salt_api_uri,
            console_type='novnc', **kwargs):

        # match suffix
        ctl_nodes = [i.host + "*" for i in self.admin_clients("nova").services.list(binary='nova-consoleauth')]

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)

        server = self._boot_server(image, flavor, **kwargs)

        index = 0
        try:
            for node in ctl_nodes:
                index = index + 1
                cmd = [node, 'cmd.run', 'systemctl stop nova-consoleauth']
                pe.execute(cmd)

                url = self.client('nova').servers\
                          .get_vnc_console(server, console_type)\
                          .get('console', {}).get('url')
                if not url:
                    raise Exception('invalid console url')

                import requests
                res = requests.get(url, verify=False)
                if res.status_code >= 400 and index < len(ctl_nodes) - 1:
                    raise Exception('access console failed')

        except Exception as e:
            LOG.error(e)
            raise
        finally:
            for node in ctl_nodes:
                try:
                    cmd = [node, 'cmd.run', 'systemctl start nova-consoleauth']
                    pe.execute(cmd)
                except Exception:
                    pass


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(context={"cleanup@openstack": ["nova"]},
                    name="InspurPlugin.nova_compute_ha",
                    platform="openstack")
class NovaComputeHa(utils.NovaScenario):

    def _boot_server_return_host(self, image, flavor, **kwargs):
        server = self._boot_server(image, flavor, **kwargs)
        return server, getattr(server, 'OS-EXT-SRV-ATTR:host')

    def _reboot_server(self, server, ignore_error=False):
        try:
            self.client('nova').servers.reboot(server)
        except Exception as e:
            LOG.error(e)
            if not ignore_error:
               raise e

    def run(self, image, flavor, salt_passwd=CONF.salt_passwd, salt_api_url=CONF.salt_api_uri, **kwargs):

        pe = PepperExecutor(uri=salt_api_url, passwd=salt_passwd)
        cmp_nodes = []
        server01, host01 = self._boot_server_return_host(image, flavor, **kwargs)
        try:
            pe.execute([host01 + '*', 'cmd.run', 'systemctl stop nova-compute'])
            self._reboot_server(server01)
            server02, host02 = self._boot_server_return_host(image, flavor, **kwargs)
            self._reboot_server(server02)
            pe.execute([host01 + '*', 'cmd.run', 'systemctl start nova-compute'])
            self._reboot_server(server01)
        except Exception as e:
            LOG.error(e)
            raise
        finally:
            for node in cmp_nodes:
                try:
                    cmd = [node, 'cmd.run', 'systemctl start nova-compute']
                    pe.execute(cmd)
                except Exception:
                    pass