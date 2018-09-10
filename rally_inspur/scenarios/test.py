import jsonschema
from rally.common import logging
from rally import exceptions as rally_exceptions
from rally.task import types
from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.cinder import utils as cinder_utils
from rally_openstack.scenarios.neutron import utils as neutron_utils
from rally_openstack.scenarios.nova import utils
from rally_openstack.wrappers import network as network_wrapper


@validation.add("required_services", services=[consts.Service.NOVA])
@validation.add("required_platform", platform="openstack", users=True)
@scenario.configure(name="SjtPlugin.list_servers", platform="openstack")
class ListServers(utils.NovaScenario):

    def run(self, detailed=True):
        """List all servers.

        This simple scenario test the nova list command by listing
        all the servers.

        :param detailed: True if detailed information about servers
                         should be listed
        """
        servers = self._list_servers(detailed)
        print(len(servers))
