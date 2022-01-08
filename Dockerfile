FROM all-officialdfy-docker.artifactory.si.francetelecom.fr/ubuntu:18.04-minimal

MAINTAINER dfy.hbx.pfs-scp.all@list.orangeportails.net

LABEL org.opencontainers.image.authors="dfy.hbx.pfs-scp.all@list.orangeportails.net" \
      org.opencontainers.image.description="Service netsniff to check page ressources (content is in HTTPS and response code)" \
      org.opencontainers.image.documentation="https://gitlab.si.francetelecom.fr/service-netsniff/service-netsniff-netsniff-gtags-builder/blob/master/README.md" \
      org.opencontainers.image.source="https://gitlab.si.francetelecom.fr/service-netsniff/service-netsniff-netsniff-gtags-builder/blob/master/README.md" \
      org.opencontainers.image.title="Service Netsniff" \
      org.opencontainers.image.url="service-tms-docker.artifactory.si.francetelecom.fr/service-tms-docker/netsniff" \
      org.opencontainers.image.vendor="dfy.hbx.pfs-scp.all@list.orangeportails.net" \
      org.opencontainers.image.version="{{ version }}"

RUN apt update \
 && apt install -y --no-install-recommends python3 python3-pip \ 
 && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* 



RUN python3 -m pip install \
            --index-url=https://artifactory.si.francetelecom.fr/api/pypi/ext_pypi/simple/ dumb-init

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.12/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=048b95b48b708983effb2e5c935a1ef8483d9e3e
 

RUN curl -fsSLO $SUPERCRONIC_URL \
 && echo "$SUPERCRONIC_SHA1SUM  $SUPERCRONIC" | sha1sum -c - \
 && chmod +x $SUPERCRONIC \
 && mv $SUPERCRONIC /usr/local/bin/$SUPERCRONIC \
 && ln -s /usr/local/bin/$SUPERCRONIC /usr/local/bin/supercronic


RUN echo "deb https://artifactory.si.francetelecom.fr/ext-debian-nodejs/node_16.x bionic main"        > /etc/apt/sources.list.d/ext-debian-nodejs.list \ 
 && echo "deb https://artifactory.si.francetelecom.fr/sfy-mdcs-eui_debian bionic main"                > /etc/apt/sources.list.d/mdcs_bionic_prod.list \
 && echo "deb https://artifactory.si.francetelecom.fr:443/dom-rsx-debian/ bionic all"                 > /etc/apt/sources.list.d/dom-rsx-debian.list \
 && echo "deb https://artifactory.packages.install-os.multis.p.fti.net/pfs-noh_debian_vdc bionic all" > /etc/apt/sources.list.d/vhype.list \
 && echo "deb http://ubuntu.packages.install-os.multis.p.fti.net/hebex-production xenial infra"       > /etc/apt/sources.list.d/monxymon_lib.list \
 && curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \  
 && apt update \ 
 && apt upgrade -y \
 && apt install -y --no-install-recommends curl               \
                   git                \
                   graphviz           \
                   less               \
                   mony=0.7.0         \
                   net-tools=*        \
                   nodejs             \
                   python-monxymonlib \
                   vhype2=* \
                   vim \
 && rm -rf /var/lib/apt/lists/*  /var/cache/apt/archives/* \ 
 && mkdir /etc/xymon/  \
 && chmod a+w /etc/xymon/   \
 && ln -snf /usr/share/zoneinfo/Europe/Paris /etc/localtime \
 && echo "Europe/Paris" > /etc/timezone \
 && useradd -r -U -m pptruser

COPY --chown=pptruser docker-entrypoint.sh /docker-entrypoint.sh
COPY --chown=pptruser xymonclient.cfg /etc/xymon/
COPY --chown=pptruser supercronictab /etc/crontab

USER pptruser
WORKDIR /home/pptruser

ENV NPM_CONFIG_PREFIX=/home/pptruser/.npm-global \ 
    MY_PYTHONPATH=/home/pptruser/.local \ 
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    VHYPE_USE_NETWORKLB="false"  \ 
    WORKSPACE_DIR=/home/pptruser/netsniff_workspace \
    ATTACHMENTS_DIR=attachments
    
RUN mkdir -p $WORKSPACE_DIR/$ATTACHMENTS_DIR $NPM_CONFIG_PREFIX \
 && python3 -m pip install netsniff  \
                           --trusted-host=artifactory.si.francetelecom.fr \
                           --index-url=https://artifactory.si.francetelecom.fr/api/pypi/ext_pypi/simple/ \ 
                           --extra-index-url=https://artifactory.si.francetelecom.fr/api/pypi/dom-scp-pypi/simple/ \ 
 && npm config set prefix $NPM_CONFIG_PREFIX \
 && npm config set @netsniff:registry https://artifactory.si.francetelecom.fr/api/npm/dom-scp-npm/ \
 && npm config set strict-ssl=false \ 
 && npm install -g @netsniff/netsniff-har \
 && echo "export PATH=$NPM_CONFIG_PREFIX/bin:$MY_PYTHONPATH/bin:$PATH" >> ~/.bashrc \
 && chmod +x /docker-entrypoint.sh

ENTRYPOINT ["dumb-init", "--", "/docker-entrypoint.sh"] 
