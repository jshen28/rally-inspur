from rally.task import validation
from rally.common import logging, opts

from rally_openstack import scenario
from rally_openstack import consts
from rally_openstack.services.identity import identity
from rally_openstack.scenarios.keystone.basic import KeystoneBasic
from rally_openstack.scenarios.nova import utils

from rally_inspur.pepper.cli import PepperExecutor

LOG = logging.getLogger(__name__)
CONF = opts.CONF


@validation.add("required_services", services=[consts.Service.NOVA, consts.Service.KEYSTONE])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["keystone", "nova"]},
                    name="InspurPlugin.keystone_ha",
                    platform="openstack")
class KeystoneHa(KeystoneBasic, utils.NovaScenario):

    def run(self, binary="apache2", salt_api_uri=CONF.salt_api_uri, salt_user_passwd=CONF.salt_passwd, **kwargs):
        """verify keystone availability

        :param binary: service name
        :param salt_api_uri:
        :param salt_user_passwd:
        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)

        hosts = [i.host for i in self.admin_clients('nova').services.list(binary='nova-conductor')]

        index = 0
        try:
            for host in hosts:
                index = index + 1
                pe.execute([host + "*", 'cmd.run', 'systemctl stop %s' % binary])
                try:
                    self.admin_keystone.list_projects()
                except Exception as e:
                    LOG.error(e)
                    if index < len(hosts):
                        raise Exception('accessing keystone service failed!')
        except Exception as e:
            LOG.error(e)
            raise e
        finally:

            for host in hosts:
                try:
                    pe.execute([host + "*", 'cmd.run', 'systemctl start %s' % binary])
                except Exception as e:
                    LOG.error(e)
                    pass



