FROM dom-infra-registry.af.multis.p.fti.net/ubuntu-bionic:daily as builder

RUN apt update \
 && apt install -y --no-install-recommends gcc python3.6 python3-pip
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

FROM dom-infra-registry.af.multis.p.fti.net/ubuntu-bionic:daily

MAINTAINER dfy.hbx.pfs-scp.all@list.orangeportails.net

COPY --from=builder /usr/local/bin/dumb-init \
                    /usr/local/bin/dumb-init
COPY --from=builder /usr/local/bin/supercronic \
                    /usr/local/bin/supercronic

LABEL org.opencontainers.image.authors="dfy.hbx.pfs-scp.all@list.orangeportails.net" \
      org.opencontainers.image.description="Service netsniff to check page ressources (content is in HTTPS and response code)" \
      org.opencontainers.image.documentation="https://gitlab.si.francetelecom.fr/service-netsniff/service-netsniff-netsniff-gtags-builder/blob/master/README.md" \
      org.opencontainers.image.source="https://gitlab.si.francetelecom.fr/service-netsniff/service-netsniff-netsniff-gtags-builder/blob/master/README.md" \
      org.opencontainers.image.title="Service Netsniff" \
      org.opencontainers.image.url="service-tms-docker.artifactory.si.francetelecom.fr/service-tms-docker/netsniff" \
      org.opencontainers.image.vendor="dfy.hbx.pfs-scp.all@list.orangeportails.net" \
      org.opencontainers.image.version="{{ version }}"

ENV DUMB_INIT_VERSION=1.2.2 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    VHYPE_USE_NETWORKLB="false"

COPY ext-debian-nodejs.list /etc/apt/sources.list.d/ext-debian-nodejs.list

RUN curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add -

WORKDIR /root/

COPY ./requirements.txt .

RUN echo "deb https://artifactory.si.francetelecom.fr/sfy-mdcs-eui_debian bionic main"                > /etc/apt/sources.list.d/mdcs_bionic_prod.list \
 && echo "deb https://artifactory.si.francetelecom.fr:443/dom-rsx-debian/ bionic all"                 > /etc/apt/sources.list.d/dom-rsx-debian.list \
 && echo "deb https://artifactory.packages.install-os.multis.p.fti.net/pfs-noh_debian_vdc bionic all" > /etc/apt/sources.list.d/vhype.list \
 && echo "deb http://ubuntu.packages.install-os.multis.p.fti.net/hebex-production xenial infra"       > /etc/apt/sources.list.d/monxymon_lib.list

RUN apt update
RUN apt upgrade -y

RUN apt install -y curl               \
                   git                \
                   graphviz           \
                   ipython3           \
                   less               \
                   mony=0.7.0         \
                   net-tools=*        \
                   nodejs             \
                   python-monxymonlib \
                   python-webpy       \
                   python3-pip        \
                   python3-setuptools \
                   vhype2=*           \
                   vim

RUN pip3 install wheel
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt \
                           --trusted-host=artifactory.si.francetelecom.fr \
                           --index-url=https://artifactory.si.francetelecom.fr/api/pypi/ext_pypi/simple/

RUN groupadd -r pptruser \
 && useradd -r -g pptruser -G audio,video pptruser          \
 && mkdir -p /home/pptruser/.lib /home/pptruser/.config/pip \
 && chown -R pptruser:pptruser /home/pptruser               \
 && ln -snf /usr/share/zoneinfo/Europe/Paris /etc/localtime \
 && echo "Europe/Paris" > /etc/timezone

# Cleanup
RUN apt-get -qq clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --chown=pptruser iPython3-entry.sh /iPython3-entry.sh
COPY --chown=pptruser iPython3.bashrc /home/pptruser/.bashrc

RUN chmod +x /iPython3-entry.sh

WORKDIR /home/pptruser
USER pptruser

CMD ["/iPython3-entry.sh"]
