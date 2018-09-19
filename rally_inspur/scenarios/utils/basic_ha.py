from rally_openstack.scenarios.nova import utils
from rally.common import logging

from rally_inspur.pepper.cli import PepperExecutor

LOG = logging.getLogger(__name__)


class BasicNovaHa(utils.NovaScenario):

    def _exec(self, **kwargs):
        image = kwargs.get('image')
        flavor = kwargs.get('flavor')
        self._boot_server(image, flavor, **kwargs)

    def _run(self, salt_api_uri=None, salt_user_passwd=None, hosts=None, **kwargs):
        """verify keystone availability

        :param binary: service name
        :param salt_api_uri:
        :param salt_user_passwd:
        :param kwargs: Other optional parameters to create users like
                         "tenant_id", "enabled".
        """

        pe = PepperExecutor(uri=salt_api_uri, passwd=salt_user_passwd)
        hosts = hosts or [i.host for i in self.admin_clients('nova').services.list(binary='nova-conductor')]
        cmd = kwargs.get('cmd')
        restore_cmd = kwargs.get('restore')
        index = 1
        try:
            for host in sorted(hosts):
                index = index + 1
                pe.execute([host + "*", 'cmd.run', cmd])
                try:
                    self._exec(**kwargs)
                except Exception as e:
                    LOG.error(e)
                    if index < len(hosts):
                        raise Exception('accessing services failed!')
        finally:

            for host in sorted(hosts, reverse=True):
                try:
                    pe.execute([host + "*", 'cmd.run', restore_cmd])
                except Exception as e:
                    LOG.error(e)
                    pass


