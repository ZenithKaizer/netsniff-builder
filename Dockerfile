FROM dom-infra-registry.af.multis.p.fti.net/ubuntu-bionic:daily as builder

RUN apt update && apt install -y --no-install-recommends gcc python3.6 python3-pip
RUN python3 -m pip install --index-url=https://artifactory.si.francetelecom.fr/api/pypi/ext_pypi/simple/ dumb-init

FROM dom-infra-registry.af.multis.p.fti.net/ubuntu-bionic:daily

MAINTAINER dfy.hbx.pfs-scp.all@list.orangeportails.net

COPY --from=builder /usr/local/bin/dumb-init /usr/local/bin/dumb-init

LABEL org.opencontainers.image.authors="dfy.hbx.pfs-scp.all@list.orangeportails.net"
LABEL org.opencontainers.image.description="Service netsniff to check page ressources (content is in HTTPS and response code)"
LABEL org.opencontainers.image.documentation="https://gitlab.si.francetelecom.fr/service-netsniff/netsniff/blob/master/README.md"
LABEL org.opencontainers.image.source="https://gitlab.si.francetelecom.fr/pfs-hporange/netsniff"
LABEL org.opencontainers.image.title="Service Netsniff"
LABEL org.opencontainers.image.url="https://gitlab.si.francetelecom.fr/service-netsniff/netsniff/blob/master/README.md"
LABEL org.opencontainers.image.vendor="dfy.hbx.pfs-scp.all@list.orangeportails.net"
LABEL org.opencontainers.image.version="{{ version }}"

ENV DUMB_INIT_VERSION=1.2.2 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

COPY ext-debian-nodejs.list /etc/apt/sources.list.d/ext-debian-nodejs.list
RUN curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -

WORKDIR /root/

COPY ./requirements.txt .

RUN echo "deb https://artifactory.si.francetelecom.fr/sfy-mdcs-eui_debian bionic main" > /etc/apt/sources.list.d/mdcs_bionic_prod.list \
  && echo "deb https://artifactory.packages.install-os.multis.p.fti.net/pfs-noh_debian_vdc bionic all" > /etc/apt/sources.list.d/vhype.list \
  && echo "deb http://ubuntu.packages.install-os.multis.p.fti.net/hebex-production xenial infra" > /etc/apt/sources.list.d/monxymon_lib.list


RUN apt-get update && \
    apt-get install -y \
    aptitude \
    python-monxymonlib \
    python3.6 \
    python3-pip \
    python3-setuptools \
    git \
    nodejs \
    python-webpy \
    graphviz \
    curl \
    vhype \
    vim \
    mony=0.7.0 \
    && pip3 install wheel \
    && python3 -m pip install --index-url=https://artifactory.si.francetelecom.fr/api/pypi/ext_pypi/simple/ -r requirements.txt

RUN groupadd -r pptruser && useradd -r -g pptruser -G audio,video pptruser \
    && mkdir -p /home/pptruser/.lib /home/pptruser/.config/pip \
    && chown -R pptruser:pptruser /home/pptruser \
    && mkdir /etc/xymon/ \
    && mkdir /etc/netsniff/ \
    && chown -R pptruser /etc/netsniff /etc/xymon \
    && ln -snf /usr/share/zoneinfo/Europe/Paris /etc/localtime && echo "Europe/Paris" > /etc/timezone

# Cleanup
RUN apt-get -qq clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --chown=pptruser docker-entrypoint.sh /docker-entrypoint.sh

COPY --chown=pptruser config/netsniff/variables.py /etc/netsniff/variables.py

RUN chmod +x /docker-entrypoint.sh

COPY --chown=pptruser bin/netsniff-url.js /usr/local/bin/netsniff-url
COPY --chown=pptruser bin/netsniff.py /usr/local/bin/netsniff
COPY --chown=pptruser bin/ws-reload-git.py /usr/local/bin/ws-reload-git
COPY --chown=pptruser bin/git-pull-conf.sh /usr/local/bin/git-pull-conf.sh
COPY --chown=pptruser lib/ /home/pptruser/.lib/
COPY --chown=pptruser config/xymon/ /home/pptruser/xymon/
COPY --chown=pptruser bin/cleanup_vip.py /usr/local/bin/cleanup_vip

RUN chmod +x /usr/local/bin/netsniff /usr/local/bin/netsniff-url /usr/local/bin/ws-reload-git /usr/local/bin/git-pull-conf.sh /usr/local/bin/cleanup_vip

WORKDIR /home/pptruser
USER pptruser

RUN npm init -f -y && \
    npm i puppeteer puppeteer-har yaml log4js har-validator && \
    mkdir /home/pptruser/attachments

ENTRYPOINT ["/usr/local/bin/dumb-init", "--", "/docker-entrypoint.sh"]
