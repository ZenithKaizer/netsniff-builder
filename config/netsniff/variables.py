from pathlib import Path

# For swift connexion
KEYSTONE_USERNAME = "hbx-ms-netsniff"
KEYSTONE_PASSWORD = "2cS%5B1C"
KEYSTONE_AUTH_URL = "https://api.ks.orangeportails.net/public/v3/"
KEYSTONE_AUTH_VERSION = "3"
KEYSTONE_USER_DOMAIN_NAME = "scp"
KEYSTONE_PROJECT_DOMAIN_NAME = "scp"
CONST_OS_ENDPOINT_TYPE = "internal"
KEYSTONE_PROJECT_NAME = "copfs_scp_netsniff"
CONTAINER_NAME = "netsniff-data"
CONST_OBJECT_EXPIRATION_IN_SECONDS = "5184000"

# For xymon instancej
CONST_ALERT_NAME = "netsniff"

# For xymon message
xymon_red_img = '/xymon/gifs/addon/red.gif'
xymon_yellow_img = '/xymon/gifs/addon/yellow.gif'

# For get_har
CONST_PROGRAM = "nodejs"
CONST_MAIN_SCRIPT = "/usr/local/bin/netsniff-url"

# For synchronize check_conf and global_conf
ATTACHMENTS_DIR = Path("/home/pptruser/attachments")
CONF_DIR = Path("/etc/netsniff/netsniff-conf/confs")
CONF_NETSNIFF = list(CONF_DIR.glob('*conf.yml'))
CHECK_NETSNIFF = list(CONF_DIR.glob('*checks.yml'))

# Thread config
queue_max_size = 0
threads_num = 15

# For get_bad_certificates()
CURL_BIN = '/usr/bin/curl'
CURL_FLAGS = '-I -s -S -g'
CURL_RETRY_NUMBER = 1
