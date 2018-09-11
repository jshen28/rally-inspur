from pepper.cli import PepperCli
import sys
import os
import json


class PepperExecutor(object):

    def __init__(self, uri=None, eauth='pam', user='salt', passwd=None):
        self.uri = uri
        self.eauth = eauth
        self.user = user
        self.passwd = passwd

    def execute(self, cmd):
        """
        workaround for invoking pepper functions without
        this function does not provide error handling,
        so user should handle them accordingly
        :param [] cmd: a list of commands
        :return: generator of salt cmd result
        """

        os.environ['SALTAPI_URL'] = self.uri
        os.environ['SALTAPI_EAUTH'] = self.eauth
        os.environ['SALTAPI_USER'] = self.user
        os.environ['SALTAPI_PASS'] = self.passwd

        # manually assemble pass-in values
        if not isinstance(cmd, (list, tuple)):
            cmd = [cmd]

        sys.argv = sys.argv + cmd

        cli = PepperCli()
        for exit_code, result in cli.run():
            if exit_code == 0:
                # print(result)
                yield json.loads(result)
            else:
                raise Exception('error executing command')

