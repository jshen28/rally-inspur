from keystoneauth1 import loading
from keystoneauth1 import session
from novaclient import client


if __name__ == '__main__':
    username = ''
    password = ''
    project_name = ''
    auth_url = ''

    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(auth_url="https://10.110.25.117:5000",
                                    username='sjt',
                                    password='sjt',
                                    project_name='sjt')
    sess = session.Session(auth=auth)
    nova = client.Client('2', session=sess, insecure=True)

    for service in nova.services.list(binary='nova-conductor'):
        print(service.host)

    for server in nova.servers.list():
        print(server.name, server.id, server.networks.values()[0][0])
        print(server.networks)
        print(dir(server))
        print(getattr(server, 'OS-EXT-SRV-ATTR:host'))
        url = nova.servers.get_vnc_console(server, 'novnc').get('console', {}).get('url')

    for server in nova.servers.list():
        print(nova.servers.reboot(server))




