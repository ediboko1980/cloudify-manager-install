FROM centos:7

ARG rpm_file=cloudify-manager-install.rpm
RUN useradd -ms /bin/bash --home-dir /etc/cloudify cfyuser

# This should save some time for the installations of all these programs
RUN yum install -y deltarpm
RUN yum install -y epel-release
RUN yum install -y initscripts sudo openssh-server systemd-sysv openssl-1.0.2k \
    libselinux-utils logrotate python-setuptools \
    python-backports python-backports-ssl_match_hostname which cronie
RUN yum install -y supervisor

EXPOSE 22 80 443 5671 5672 53333

# Should help to stop the container gracfully

COPY $rpm_file /tmp/cloudify-manager-install.rpm
RUN yum install -y /tmp/cloudify-manager-install.rpm && rm /tmp/cloudify-manager-install.rpm
COPY config.yaml /etc/cloudify/config.yaml
COPY starter.sh /opt/cloudify-starter.sh
RUN chmod +x /opt/cloudify-starter.sh
RUN cfy_manager install --only-install --verbose
RUN chown cfyuser: -R /var/log/cloudify
RUN mkdir -p /var/log/supervisor && chown cfyuser: /var/log/supervisor
RUN chown cfyuser: /etc/supervisord.d
RUN chown cfyuser: -R /var/lib/pgsql
RUN chown cfyuser: -R /var/lib/rabbitmq
RUN chown cfyuser: -R /etc/cloudify/rabbitmq
RUN chown cfyuser: -R /etc/rabbitmq
RUN chown cfyuser: -R /var/run/postgresql
RUN chown cfyuser: -R /var/log/rabbitmq
RUN chown cfyuser: -R /etc/nginx
RUN chown cfyuser: -R /etc/cloudify
RUN chown cfyuser: /opt/manager
RUN chown cfyuser: /opt/cloudify
RUN mkdir /run/cloudify-restservice && chown cfyuser: /run/cloudify-restservice
RUN chown cfyuser: /var/cache/nginx
RUN chown cfyuser: -R /var/log/nginx
RUN chown cfyuser: -R /opt/nodejs
RUN chown cfyuser: -R /opt/cloudify-stage
RUN chown cfyuser: -R /opt/cloudify-composer
RUN chmod a+wx /var/run
RUN rm /etc/cloudify/config.yaml
USER cfyuser
COPY supervisord.conf /etc/supervisord.conf
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisord.conf"]
