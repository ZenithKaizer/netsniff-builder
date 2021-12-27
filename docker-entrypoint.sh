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
    #vhype -v use-environment add
fi

if [ -z "$WORKSPACE_DIR" ]; then
    echo "Variable WORKSPACE_DIR must be defined."
    exit 1
fi

if [ -z "$CONFIG_NAME" ]; then
    echo "Variable CONFIG_NAME must be defined. Can be hporange, gtags, adgateway, malvertizing"
    exit 1
fi

if [ -z "$ATTACHMENTS_DIR" ]; then
    echo "Variable ATTACHMENTS_DIR must be defined."
    exit 1
fi

if [ -z "$BROWSERLESS_URL" ]; then
    echo "Variable BROWSERLESS_URL must be defined."
    exit 1
fi

if [ -z "$XYMON_SERVERS" ]; then
    echo "Variable XYMON_SERVERS must be defined."
    exit 1
fi

export CONF_DIR=$WORKSPACE_DIR/netsniff-conf

if [ ! -d $CONF_DIR/.git ]; then
    git clone https://$GITLAB_USER:$GITLAB_PASSWORD@gitlab.si.francetelecom.fr/service-netsniff/netsniff-conf.git $CONF_DIR
fi


# sed xymonclient.cfg with $XYMSERVERS env var
 sed -i "s/XYMON_SERVERS/$XYMON_SERVERS/g" /etc/xymon/xymonclient.cfg

cat /etc/crontab ; echo
/usr/local/bin/supercronic -passthrough-logs /etc/crontab 2>&1 &

export PATH=~/.npm-global/bin:~/.local/bin:$PATH

netsniff-hp -c $CONF_DIR -t $CONFIG_NAME -a $WORKSPACE_DIR/$ATTACHMENTS_DIR -b $BROWSERLESS_URL &

netsniff-conf-ws &

wait -n
