from keystoneauth1 import loading
from keystoneauth1 import session
from neutronclient.v2_0 import client
from novaclient import client as nova_client

if __name__ == '__main__':
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


    def get_network_and_subnets_by_name(network_name):

        for network in neutron.list_networks().get('networks', []):
            if network.get('name') == network_name:
                break

        network = neutron.show_network(network.get('id'))
        subnets = neutron.list_subnets(network_id=network['network']['id'])

        return network, subnets


    def print_dhcp_agent_by_network(network_id):
        print(neutron.list_dhcp_agent_hosting_networks(network_id))


    def create_router(body):
        return neutron.create_router(body)


    def get_l3_agent_by_router(router_id):
        return neutron.list_l3_agent_hosting_routers(router_id)


    def show_router(router_name):

        for router in neutron.list_routers()['routers']:
            if router['name'] == router_name:
                break

        return neutron.show_router(router['id'])


    network_readable_name = 'vlan-156'
    network, subnets = get_network_and_subnets_by_name(network_readable_name)

    # for i in neutron.list_agents(binary='neutron-dhcp-agent', network=network.get('id')).get('agents', []):
    #     print(i.get('host'), i.get('admin_state_up'))

    router_name = 'vr'
    # router = create_router({
    #     "router": {
    #         'name': router_name,
    #         'external_gateway_info': {
    #             'network_id': network['subnets'][0]['network']['id'],
    #             'enable_snat': True
    #         }
    #     }
    # })

    router = show_router(router_name)
    print(router)

    # neutron.add_interface_router(router['router']['id'], {
    #     'subnet_id': subnets[0]['subnet']['id']
    # })

    print(get_l3_agent_by_router(router['router']['id'])['agents'])
