from rally.common import cfg

opts = [
    cfg.StrOpt("salt_api_uri", default='',
               help="salt api uri"),
    cfg.StrOpt("salt_user", default='salt',
               help="salt api user"),
    cfg.StrOpt("salt_passwd", default='',
               help="salt password"),
    cfg.StrOpt('salt_eauth', default='pam',
               help='salt authorization method')
]

cfg.CONF.register_opts(opts)
