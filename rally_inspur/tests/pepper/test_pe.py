from rally_inspur.pepper.cli import PepperExecutor

if __name__ == '__main__':

    # avoid automatically loading this script
    pe = PepperExecutor(uri='http://10.110.25.118:6969', passwd='iBqfXC9QQBhdi8C8XmrkeClF45qyTaGq')

    target = '*'
    cmd1 = 'cmd.run'
    cmd2 = 'echo "hello world"'

    for i in pe.execute(['*', 'test.ping']):
        print(i)
