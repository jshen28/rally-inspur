from rally_inspur.tests.pepper.test_sup import TestSup
import socket


socket.getaddrinfo()


class TestSub(TestSup):

    def __init__(self):
        print('hello sub')



