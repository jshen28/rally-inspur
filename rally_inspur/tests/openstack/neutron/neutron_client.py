from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.v2_0 import client
from novaclient import client as nova_client

username = ''
password = ''
project_name = ''
auth_url = ''

loader = loading.get_plugin_loader('password')
auth = loader.load_from_options(auth_url="https://10.110.25.117:35357",
                                username='sjt',
                                password='sjt',
                                project_name='sjt')
sess = session.Session(auth=auth, verify=False)
neutron = client.Client(session=sess, insecure=True)
nova = nova_client.Client('2', session=sess, insecure=True)

print(dir(neutron))

print(dir(neutron.list_networks()))

for i in neutron.list_agents(binary='neutron-dhcp-agent').get('agents', []):
    print(i.get('host'), i.get('admin_state_up'))

network = neutron.create_network(
    {
        "network":
            {
                "name": "client-test"
            }
    }
)
subnet = neutron.create_subnet(
    {
        "subnet":
            {
                "network_id": network.get('network', {}).get('id'),
                "name": "test",
                "cidr": "10.7.0.0/24",
                "ip_version": "4"
            }
    }
)

nova.servers.create('test-client', '9bedcbbd-492f-4bd9-9221-84165a0d2e47', '0a0d73cb-db2a-424a-969b-b060f76431f4', nics=[
    {"net-id": network.get('network', {}).get('id')}
])
print(network, subnet)
