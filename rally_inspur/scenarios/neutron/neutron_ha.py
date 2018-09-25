# Copyright 2014: Intel Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from rally_inspur.pepper.cli import PepperExecutor
from rally.task import validation, types
from rally.task import utils as rally_utils
from rally import exceptions
from rally.task import atomic

from rally_openstack import consts
from rally_openstack import scenario
from rally_openstack.scenarios.neutron import utils
from rally_openstack.scenarios.nova import utils as nova_utils
from rally_openstack.wrappers import network as network_wrapper
from rally.common import cfg, logging

import shlex
import subprocess

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class NeutronHaTest(utils.NeutronScenario, nova_utils.NovaScenario):

    def _get_agent_hosts(self, binary=None, **kwargs):

        if kwargs.get('network'):
            hosts = [(i.get('host'), i.get('admin_state_up'))
                     for i in self.admin_clients('neutron').
                     list_dhcp_agent_hosting_networks(kwargs.get('network')).get('agents', [])]
        elif kwargs.get('router'):
            hosts = [(i.get('host'), i.get('admin_state_up'))
                     for i in self.admin_clients('neutron').
                     list_l3_agent_hosting_routers(kwargs.get('router')).get('agents')]
        else:
            hosts = [(i.get('host'), i.get('admin_state_up'))
                     for i in self.admin_clients('neutron').list_agents(binary=binary, **kwargs).get('agents', [])]
        return hosts

    def _boot_server(self, image, flavor, auto_assign_nic=False, **kwargs):

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

        server = self.clients("nova").servers.create(
            server_name, image, flavor, **kwargs)

        self.sleep_between(CONF.openstack.nova_server_boot_prepoll_delay)
        server = rally_utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=rally_utils.get_from_manager(),
            timeout=CONF.openstack.nova_server_boot_timeout,
            check_interval=CONF.openstack.nova_server_boot_poll_interval
        )
        return server

    def _boot_server_admin(self, image, flavor, auto_assign_nic=False, **kwargs):
        """Boot a server.

        Returns when the server is actually booted and in "ACTIVE" state.

        If multiple networks created by Network context are present, the first
        network found that isn't associated with a floating IP pool is used.

        :param image: image ID or instance for server creation
        :param flavor: int, flavor ID or instance for server creation
        :param auto_assign_nic: bool, whether or not to auto assign NICs
        :param kwargs: other optional parameters to initialize the server
        :returns: nova Server instance
        """
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

        server = self.admin_clients("nova").servers.create(
            server_name, image, flavor, **kwargs)

        self.sleep_between(CONF.openstack.nova_server_boot_prepoll_delay)
        server = rally_utils.wait_for_status(
            server,
            ready_statuses=["ACTIVE"],
            update_resource=rally_utils.get_from_manager(),
            timeout=CONF.openstack.nova_server_boot_timeout,
            check_interval=CONF.openstack.nova_server_boot_poll_interval
        )
        return server

    def _delete_server_admin(self, server):
        # (fixme) wait for successfully deleting server
        self.admin_clients('nova').servers.delete(server)

    def _detach_nic(self, server, only_one=True):
        nova = self.admin_clients('nova')
        attachments = nova.servers.interface_list(server)

        for attachment in attachments:
            nova.servers.interface_detach(server, attachment.port_id)
            serverng = getattr(nova.servers, 'get')(server)
            LOG.info('server %s status %s' % (server.id, serverng.status))

            import time
            time.sleep(10)

            # it looks to me that interface detaching is synchronous rightnow
            if attachment.port_id in self._list_interfaces(server):
                raise Exception('detaching interface failed')

            if only_one:
                break

    def _list_interfaces(self, server):
        nova = self.admin_clients('nova')
        attachments = nova.servers.interface_list(server)

        interface_list = []
        for attachment in attachments:
            interface_list.append(attachment.port_id)
        return interface_list

    def _create_and_associate_floating_ip_admin(self, server, **create_floating_ip_args):
        """
        create and associate floating ip to specified server
        :param server:
        :param create_floating_ip_args:
        :return:
        """

        address = network_wrapper.wrap(self.admin_clients, self).create_floating_ip(
            tenant_id=server.tenant_id, **create_floating_ip_args)
        self._associate_floating_ip_admin(server, address["ip"])
        return address['ip']

    @atomic.action_timer("nova.associate_floating_ip")
    def _associate_floating_ip_admin(self, server, address, fixed_address=None):
        """Add floating IP to an instance

        :param server: The :class:`Server` to add an IP to.
        :param address: The dict-like representation of FloatingIP to add
            to the instance
        :param fixed_address: The fixedIP address the FloatingIP is to be
               associated with (optional)
        """
        with atomic.ActionTimer(self, "neutron.list_ports"):
            ports = self.admin_clients("neutron").list_ports(device_id=server.id)
            port = ports["ports"][0]

        fip = address
        if not isinstance(address, dict):
            LOG.warning(
                "The argument 'address' of "
                "NovaScenario._associate_floating_ip method accepts a "
                "dict-like representation of floating ip. Transmitting a "
                "string with just an IP is deprecated.")
            with atomic.ActionTimer(self, "neutron.list_floating_ips"):
                all_fips = self.admin_clients("neutron").list_floatingips(
                    tenant_id=self.context["tenant"]["id"])
            filtered_fip = [f for f in all_fips["floatingips"]
                            if f["floating_ip_address"] == address]
            if not filtered_fip:
                raise exceptions.NotFoundException(
                    "There is no floating ip with '%s' address." % address)
            fip = filtered_fip[0]
        # the first case: fip object is returned from network wrapper
        # the second case: from neutronclient directly
        fip_ip = fip.get("ip", fip.get("floating_ip_address", None))
        fip_update_dict = {"port_id": port["id"]}
        if fixed_address:
            fip_update_dict["fixed_ip_address"] = fixed_address
        self.admin_lients("neutron").update_floatingip(
            fip["id"], {"floatingip": fip_update_dict}
        )
        utils.wait_for(server,
                       is_ready=self.check_ip_address(fip_ip),
                       update_resource=utils.get_from_manager())
        # Update server data
        server.addresses = server.manager.get(server.id).addresses

    def _ping_server(self, host, pe, network_id, ip, timeout=60):
        """
        ping server ip
        :param host: host where dhcp namespace resdies
        :param pe: Pepper Executor instance
        :param network_id: network id
        :param ip: server ip
        :return:
        """

        import time

        # wait for server to boot up
        LOG.info('sleep  for %d seconds' % timeout)
        time.sleep(timeout)

        # ping server in associate namespace
        cmd = [host + "*"]
        cmd.append('cmd.run')
        cmd.append('ip netns exec qdhcp-%s ping -c 3 %s 2>/dev/null 1>&2; echo $?' % (network_id, ip))
        try:
            LOG.info('cmd is %s' % cmd)
            result = pe.execute_return_exit_code(cmd)
            LOG.info(result)
            return True
        except Exception as e:
            LOG.error(e)
            return False

    def _ssh_server(self, ip, username='cirros', password='gocubsgo'):
        """
        ssh ip & print helloworld
        :param ip:
        :param username:
        :param password:
        :return:
        """

        # subprocess.Popen will throw an error if command does not exist
        p = subprocess.Popen(['apt', 'install', '-y', 'sshpass'], stdout=subprocess.PIPE)
        return_tuple = p.communicate()

        if p.returncode != 0:
            raise Exception(return_tuple[1])

        cmd = 'sshpass -p %s ssh %s@%s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "echo HelloWorld"' % (password, username, ip)
        p = subprocess.Popen(*shlex.split(cmd), stdout=subprocess.PIPE)
        return_tuple = p.communicate()

        if p.returncode != 0:
            raise Exception(return_tuple[1])

    def _ping_from_server(self, ip, username, password, host, network_id, pe, cmd='ping -c 3', dest="114.114.114.114"):
        """
        ping in server
        first install sshpass to avoid inputing password
        second ssh into vm from corresponding namespace and ping baidu dns server (114.114.114.114)
        :param ip: ip address
        :param username:
        :param password:
        :param host: host on which executing ping command
        :param network_id: neutron network id
        :param pe: pepper executor instance
        :param cmd: command
        :param dest: destine ip address (default 114.114.114.114)
        :return:
        """

        try:
            # install sshpass
            pe.execute([
                host + "*",
                'cmd.run',
                'sudo apt install -y sshpass'
            ])

            # execute ping using ssh
            cmd = [
                host + "*",
                'cmd.run',
                'ip netns exec qdhcp-%s sshpass -p "%s" ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s@%s "%s %s" 2>/dev/null 1>&2; echo $?'
                % (network_id, password, username, ip, cmd, dest)
            ]
            LOG.info('cmd is %s' % cmd)
            pe.execute_return_exit_code(cmd)

            return True
        except Exception as e:
            LOG.error(e)
            return False

    def _remove_namespace(self, host, pe, id, ns_type='snat'):
        if ns_type == 'snat':
            namespace = 'snat-' + id
        elif ns_type == 'router':
            namespace = 'qrouter-' + id
        else:
            namespace = 'qdhcp-' + id
        cmd = [
            host + '*',
            'cmd.run',
            'ip netns delete %s' % namespace
        ]
        LOG.info('cmd is %s' % cmd)
        pe.execute(cmd)

    def _kill_dnsmasq(self, host, pe, network_id):
        """
        kill dnsmasq for a given network
        :param host: gateway node
        :param pe: pepper executor instance
        :param network_id: netowrk id
        """

        cmd = list(host+'*')
        cmd.append('cmd.run')
        cmd.append("ps -ef | grep %s | awk '{print $2}' | xargs kill -9 " % network_id)
        pe.execute(cmd)

    def _get_compute_host(self):
        """
        list all nova-compute hosts
        :return:
        """
        return [i.host for i in self._list_services(binary='nova-compute')]


@validation.add("required_services",
                services=[consts.Service.NOVA, consts.Service.NEUTRON])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_server_ha",
                    platform="openstack")
class NeutronServerHa(NeutronHaTest, nova_utils.NovaScenario):

    def run(self, network_create_args=None, salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd):
        """verify neutron server availability

        :param salt_api_uri
        :param salt_user_passwd
        :param network_create_args: dict, POST /v2.0/networks request options
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)
        index = 0
        hosts = [i.host for i in self.admin_clients("nova").services.list(binary='nova-conductor')]
        try:
            for host in hosts:
                index = index + 1
                LOG.info('stop neutron-server on host %s' % host)
                pe.execute([host + '*', 'cmd.run', 'systemctl stop neutron-server'])
                _ = self._create_network(network_create_args or {})
        except Exception as e:
            LOG.error(e)
            if index < len(hosts):
                raise e
        finally:
            try:
                for host in hosts:
                    LOG.info('start neutron-server on host %s' % host)
                    pe.execute([host + "*", 'cmd.run', 'systemctl start neutron-server'])
            except Exception as e:
                LOG.error(e)

            import time
            LOG.info('wait for 15s before continuing')
            time.sleep(15)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services",
                services=[consts.Service.NEUTRON, consts.Service.NOVA])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_dhcp_agent_ha",
                    platform="openstack")
class NeutronDhcpAgentHa(NeutronHaTest, nova_utils.NovaScenario):

    def run(self, image, flavor, network_create_args=None,
            salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """verify neutron dhcp agent availability

        :param image: image name (will be auto converted to id)
        :param flavor: flavor name (will be auto converted to id)
        :param network_create_args: dict, POST /v2.0/networks request options
        :param salt_api_uri
        :param salt_user_passwd
        """

        network, subnets = self._create_network_and_subnets(network_create_args or {})
        network_id = network.get('network', {}).get('id')
        kwargs.update({'nics': [{"net-id": network_id}]})
        server = self._boot_server(image, flavor, **kwargs)
        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)
        binary = 'neutron-dhcp-agent'
        index = 0
        try:
            hosts = self._get_agent_hosts(network=network_id)
            LOG.info('dhcp agents %s host network %s' % (hosts, network_id))
            for host, _ in hosts:
                index = index + 1

                # stop dhcp agent & kill dnsmasq
                # after this server will not be able to get dhcp
                pe.execute([host + '*', 'cmd.run', 'systemctl stop %s' % binary])
                self._kill_dnsmasq(host, pe, network_id)
                self._do_server_reboot(server, "HARD")

                # server could have multiple NICs over multiple networks
                # for simplicity assumes single interface is attached
                ok = self._ping_server(host, pe, network_id, server.networks.values()[0][0])
                if not ok and index < len(hosts):
                    raise Exception('server could not get its ip')
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            try:
                for host, state in self._get_agent_hosts(network=network_id):
                    LOG.info('start dhcp-agent on host %s' % host)
                    if state:
                        pass
                    pe.execute([host + "*", 'cmd.run', 'systemctl start %s' % binary])
            except Exception as e:
                LOG.error(e)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services",
                services=[consts.Service.NEUTRON, consts.Service.NOVA])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_l3_agent_ha",
                    platform="openstack")
class NeutronL3AgentHa(NeutronHaTest):

    def run(self, image, flavor, username='cirros', password='cubswin:)', network_create_args=None, router_create_args=None,
            salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """verify neutron l3 agent availability

        :param image: image name (will be auto converted to id)
        :param flavor: flavor name (will be auto converted to id)
        :param username: vm username
        :param password: vm password
        :param network_create_args: dict, POST /v2.0/networks request options
        :param router_create_args: dict
        :param salt_api_uri
        :param salt_user_passwd
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)

        # create network & subnet
        network, subnets = self._create_network_and_subnets(network_create_args or {})

        # create router and add interface
        router = self._create_router(router_create_args or {}, )
        self._add_interface_router(subnets[0]['subnet'], router['router'])

        # save router id & network id
        router_id = router['router']['id']
        network_id = network.get('network', {}).get('id')

        # boot server on network
        kwargs.update({'nics': [{"net-id": network_id}]})
        server = self._boot_server_admin(image, flavor, **kwargs)

        binary = 'neutron-l3-agent'
        index = 0
        try:
            hosts = self._get_agent_hosts(router=router_id)
            LOG.debug('l3 agents %s host router %s' % (hosts, router_id))
            for host, _ in hosts:
                LOG.info('stop l3 agent on host %s' % host)
                index = index + 1

                # stop l3-agent & remove associated snat namespace
                pe.execute([host + '*', 'cmd.run', 'systemctl stop %s' % binary])
                self._remove_namespace(host, pe, router_id)

                # server could have multiple NICs over multiple networks
                # for simplicity assumes single interface is attached
                ok = self._ping_from_server(server.networks.values()[0][0], username, password,
                                            host, network['network']['id'], pe)
                if not ok and index < len(hosts):
                    raise Exception('failed access internet inside VM')
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            try:
                for host, state in self._get_agent_hosts(router=router_id):
                    if state:
                        pass
                    pe.execute([host + "*", 'cmd.run', 'systemctl start %s' % binary])
            except Exception as e:
                LOG.error(e)


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services",
                services=[consts.Service.NEUTRON, consts.Service.NOVA])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_l3_agent_floatingip_ha",
                    platform="openstack")
class NeutronL3AgentFloatingipHa(NeutronHaTest):

    def run(self, image, flavor, username='cirros', password='cubswin:)', network_create_args=None, router_create_args=None,
            salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, create_floating_ip_args=None, **kwargs):
        """verify neutron l3 agent availability

        :param image: image name (will be auto converted to id)
        :param flavor: flavor name (will be auto converted to id)
        :param username: vm username
        :param password: vm password
        :param network_create_args: dict, POST /v2.0/networks request options
        :param router_create_args: dict
        :param salt_api_uri
        :param salt_user_passwd
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)
        hosts = [i for i in self._get_compute_host() if i.startswith('cmp')]

        if len(hosts) < 2:
            raise Exception('Not enough compute host')

        # create network & subnet
        network, subnets = self._create_network_and_subnets(network_create_args or {})

        # create router and add interface
        router = self._create_router(router_create_args or {}, )
        self._add_interface_router(subnets[0]['subnet'], router['router'])

        # save router id & network id
        router_id = router['router']['id']
        network_id = network.get('network', {}).get('id')

        # boot server on network
        kwargs.update({'nics': [{"net-id": network_id}],
                       "availability-zone": ":%s" % hosts[0]})
        server = self._boot_server_admin(image, flavor, **kwargs)
        ip = self._create_and_associate_floating_ip_admin(server, **create_floating_ip_args)

        kwargs.update({'nics': [{"net-id": network_id}],
                       "availability-zone": ":%s" % hosts[1]})
        server02 = self._boot_server_admin(image, flavor, **kwargs)
        ip02 = self._create_and_associate_floating_ip_admin(server, **create_floating_ip_args)

        binary = 'neutron-l3-agent'
        index = 0
        try:
            LOG.debug('l3 agents %s host router %s' % (hosts, router_id))
            LOG.info('stop l3 agent on host %s' % (hosts[0]))
            index = index + 1

            # stop l3-agent & remove associated snat namespace
            self._ssh_server(ip, username=username, password=password)
            pe.execute([hosts[0] + '*', 'cmd.run', 'systemctl stop %s' % binary])
            self._remove_namespace(hosts[0], pe, router_id, ns_type='router')
            try:
                # floating ip as well as fixed ip will not be accessible outside of
                # vxlan network
                self._ssh_server(ip, username=username, password=password)
            except Exception:
                pass
            else:
                # throw exception if there is no exception reported
                raise Exception('should not be able to log in')

            self._ssh_server(ip02, username=username, password=password)
        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            try:
                pe.execute([hosts[0] + "*", 'cmd.run', 'systemctl start %s' % binary])
            except Exception as e:
                LOG.error(e)
            try:
                # delete server created by admin user
                self._delete_server_admin(server)
                self._delete_server_admin(server02)
            except Exception:
                pass


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services",
                services=[consts.Service.NEUTRON, consts.Service.NOVA])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_ovs_agent_ha",
                    platform="openstack")
class NeutronOvsAgentHa(NeutronHaTest):

    def run(self, image, flavor, username='cirros', password='cubswin:)', network_create_args=None,
            salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """verify neutron ovs agent availability.

        :param image: image name (will be auto converted to id)
        :param flavor: flavor name (will be auto converted to id)
        :param username: vm username
        :param password: vm password
        :param network_create_args: dict, POST /v2.0/networks request options
        :param salt_api_uri
        :param salt_user_passwd
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)

        # create network & subnet
        network, subnets = self._create_network_and_subnets(network_create_args or {})

        # save router id & network id
        network_id = network.get('network', {}).get('id')
        # list all nova-compute hosts
        hosts = self._get_compute_host()
        # boot server on network
        kwargs.update({'nics': [{"net-id": network_id}]})
        # designate server to compute node
        kwargs.update({'availability_zone': ":%s" % hosts[0]})
        server = self._boot_server_admin(image, flavor, **kwargs)
        kwargs.update({'availability_zone': ":%s" % hosts[1]})
        server02 = self._boot_server_admin(image, flavor, **kwargs)

        # get gateway host
        gtw, _ = self._get_agent_hosts(network=network_id)[0]

        # binary = 'neutron-openvswitch-agent'
        binary = 'nova-compute'
        try:
            LOG.debug('stop l3 agent on %s host' % hosts[0])

            # server could have multiple NICs over multiple networks
            # for simplicity assumes single interface is attached
            LOG.info('wait 60s for bootup')
            import time
            time.sleep(60)
            ip02 = server02.networks.values()[0][0]
            ok = self._ping_from_server(server.networks.values()[0][0], username, password,
                                        gtw, network_id, pe, dest=ip02)

            if not ok:
                raise Exception("failed accessing %s, network issue" % ip02)

            # stop ovs agent
            LOG.info('stop nova-compute on %s' % hosts[0])
            pe.execute([hosts[0] + '*', 'cmd.run', 'systemctl stop %s' % binary])

            # intercept this exception
            # FIXME (is interface detaching async?)
            try:
                self._detach_nic(server)
            except Exception as e:
                LOG.error(e)

            # server02 is ok
            self._detach_nic(server02)

            # fixme this is not correct.
            import time
            LOG.info('wait 60s allowing detaching successfully')
            time.sleep(60)

            # restart ovs-agent
            pe.execute([hosts[0] + '*', 'cmd.run', 'systemctl start %s' % binary])

            # wait for 10s before continuing
            time.sleep(10)
            LOG.info('waiting 10s for neutron-openvswitch-agent')

            # try again
            self._detach_nic(server)

        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            pe.execute([hosts[0] + '*', 'cmd.run', 'systemctl start %s' % binary])


@types.convert(image={"type": "glance_image"},
               flavor={"type": "nova_flavor"})
@validation.add("image_valid_on_flavor", flavor_param="flavor",
                image_param="image")
@validation.add("required_services",
                services=[consts.Service.NEUTRON, consts.Service.NOVA])
@scenario.configure(context={"cleanup@openstack": ["nova", "neutron"]},
                    name="InspurPlugin.neutron_metadata_agent_ha",
                    platform="openstack")
class NeutronMetadataAgentHa(NeutronHaTest):

    def run(self, image, flavor, username='cirros', password='cubswin:)', network_create_args=None,
            salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """verify neutron metdata service availability

        :param image: image name (will be auto converted to id)
        :param flavor: flavor name (will be auto converted to id)
        :param username: vm username
        :param password: vm password
        :param network_create_args: dict, POST /v2.0/networks request options
        :param salt_api_uri
        :param salt_user_passwd
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)

        # create network & subnet
        network, subnets = self._create_network_and_subnets(network_create_args or {})

        # save router id & network id
        network_id = network.get('network', {}).get('id')

        # boot server on network
        kwargs.update({'nics': [{"net-id": network_id}]})
        server = self._boot_server(image, flavor, **kwargs)

        server_detail = getattr(self.admin_clients('nova').servers, "get")(server)
        cmp_host = getattr(server_detail, 'OS-EXT-SRV-ATTR:host')

        binary = 'neutron-metadata-agent'
        index = 0
        hosts = [i for i, _ in self._get_agent_hosts(binary='neutron-dhcp-agent')]
        hosts.append(cmp_host)
        try:
            LOG.debug('metadata agents running on hosts: %s' % hosts)
            for host in hosts:
                LOG.info('stop metadata-agent on host %s' % host)
                index = index + 1

                # stop l3-agent & remove associated snat namespace
                pe.execute([host + '*', 'cmd.run', 'systemctl stop %s' % binary])

                # server could have multiple NICs over multiple networks
                # for simplicity assumes single interface is attached
                ok = self._ping_from_server(server.networks.values()[0][0], username, password,
                                            hosts[0], network_id, pe, cmd='curl', dest='169.254.169.254')
                if not ok and index < len(hosts):
                    raise Exception('failed extracting userdata from metadata service')

            # restart metadata service
            for host, state in self._get_agent_hosts(binary=binary):
                if state:
                    pass
                pe.execute([host + "*", 'cmd.run', 'systemctl start %s' % binary])

            # sleep 10s
            import time
            LOG.info('sleeping 10s and waiting for services backup')
            time.sleep(10)

            # extracting metadata
            ok = self._ping_from_server(server.networks.values()[0][0], username, password,
                                        hosts[0], network_id, pe, cmd='curl', dest='169.254.169.254')
            if not ok:
                raise Exception('failed acceessing metadata service')

        except Exception as e:
            LOG.error(e)
            raise e
        finally:
            for host in hosts:
                pe.execute([host+"*", 'cmd.run', 'systemctl restart %s' % binary])


