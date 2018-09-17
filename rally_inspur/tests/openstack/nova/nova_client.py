from keystoneauth1 import loading
from keystoneauth1 import session
from novaclient import client


username = ''
password = ''
project_name = ''
auth_url = ''

loader = loading.get_plugin_loader('password')
auth = loader.load_from_options(auth_url="",
                                username='',
                                password='',
                                project_name='')
sess = session.Session(auth=auth)
nova = client.Client('2', session=sess, insecure=True)

for service in nova.services.list(binary='nova-conductor'):
    print(service.host)

for service in nova.services.list(binary='nova-scheduler'):
    print(service.host)

for service in nova.services.list(binary='nova-consoleauth'):
    print(service.host)

for server in nova.servers.list():
    print(server.name)
    print(getattr(server, 'OS-EXT-SRV-ATTR:host'))
    url = nova.servers.get_vnc_console(server, 'novnc').get('console', {}).get('url')

    import requests
    res = requests.get(url, verify=False)
    print(res.status_code)
    # print(res.text)

for server in nova.servers.list():
    print(nova.servers.reboot(server))




