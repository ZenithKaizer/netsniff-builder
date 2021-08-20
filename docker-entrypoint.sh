#!/bin/bash -e

/usr/bin/python3 -V
echo

/usr/bin/python3 -m pip -V
echo

if [ -z "$GITLAB_USER" ]; then
    echo "Variable GITLAB_USER must be defined"
    exit 1
fi

if [ -z "$GITLAB_PASSWORD" ]; then
    echo "Variable GITLAB_PASSWORD must be defined"
    exit 1
fi

if [ -z "$WS_GIT_RELOAD_PORT" ]; then
    echo "Variable WS_GIT_RELOAD_PORT must be defined"
    exit 1
fi

if [ -z "$WS_GIT_RELOAD_TOKEN" ]; then
    echo "Variable WS_GIT_RELOAD_TOKEN must be defined"
    exit 1
fi

if [ -z "$VHYPE_USER" ]; then
    echo "Variable VHYPE_USER must be defined"
    exit 1
fi

if [ -z "$VHYPE_PASS" ]; then
    echo "Variable VHYPE_PASS must be defined"
    exit 1
fi

if [ -z "$VHYPE_VIP_NETSNIFF_HTTPS" ]; then
    echo "Variable VHYPE_VIP_NETSNIFF_HTTPS must be defined"
    exit 1
fi

if [ -n "$VHYPE_PASS" ]; then
#    echo "Cleaning up VIP"
#    /usr/local/bin/cleanup_vip
    echo "add node in VIP"
    vhype -v use-environment add
fi

cd /etc/netsniff
if [ ! -d netsniff-conf/.git ]; then
    git clone https://$GITLAB_USER:$GITLAB_PASSWORD@gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf.git
fi

cd /home/pptruser

if [ "$ENV" == "dev" ]; then
    ln -sf /home/pptruser/service-netsniff/netsniff-conf /etc/netsniff/netsniff-conf
    ln -sf /home/pptruser/service-netsniff/netsniff/bin/netsniff-url.js /usr/local/bin/netsniff-url
    ln -sf /home/pptruser/service-netsniff/netsniff/lib/netsniff-url /home/pptruser/.lib/netsniff-url
    ln -sf /home/pptruser/service-netsniff/netsniff/lib/netsniff /home/pptruser/.lib/netsniff
    ln -sf /home/pptruser/xymon/xymonclient_dev_sph.cfg /etc/xymon/xymonclient.cfg
elif [ "$ENV" == "prod" ]; then
    ln -sf /home/pptruser/xymon/xymonclient_prod.cfg /etc/xymon/xymonclient.cfg
elif [ "$ENV" == "rec" ] || [ "$ENV" == "preprod" ]; then
    ln -sf /home/pptruser/xymon/xymonclient_rec.cfg /etc/xymon/xymonclient.cfg
else
    echo "Nothing will be send to xymon"
fi

export NODE_PATH=/home/pptruser/node_modules

cat /etc/crontab
/usr/local/bin/supercronic /etc/crontab &
/usr/local/bin/netsniff &
/usr/local/bin/ws-reload-git &

wait -n
