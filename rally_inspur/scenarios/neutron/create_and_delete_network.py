from rally.task import validation

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.neutron import utils


@validation.add("required_services",
                services=[consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["neutron"]},
                    name="NSPNetworks.create_and_delete_networks",
                    platform="openstack")
class CreateAndDeleteNetworks(utils.NeutronScenario):

    def run(self, network_create_args=None):
        """Create and delete a network.
        Measure the "neutron net-create" and "net-delete" command performance.
        :param network_create_args: dict, POST /v2.0/networks request options
        """
        network = self._create_network(network_create_args or {})
        self._delete_network(network["network"])

