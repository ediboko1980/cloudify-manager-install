FROM centos:7

ARG rpm_file=cloudify-manager-install.rpm

# This should save some time for the installations of all these programs
RUN yum install -y deltarpm
RUN yum install -y epel-release
RUN yum install -y initscripts sudo openssh-server systemd-sysv openssl-1.0.2k \
    libselinux-utils logrotate python-setuptools \
    python-backports python-backports-ssl_match_hostname which cronie
RUN ssh-keygen -A

ENV container=docker

EXPOSE 22 80 443 5671 5672 53333


RUN systemctl set-default multi-user.target ; systemctl enable crond
COPY $rpm_file /tmp/cloudify-manager-install.rpm
RUN yum install -y /tmp/cloudify-manager-install.rpm && rm /tmp/cloudify-manager-install.rpm
COPY config.yaml /etc/cloudify/config.yaml
COPY starter.service /usr/lib/systemd/system/cloudify-starter.service
COPY starter.sh /opt/cloudify-starter.sh
RUN chmod +x /opt/cloudify-starter.sh && systemctl enable cloudify-starter
RUN cfy_manager install --only-install --verbose
CMD ["/sbin/init"]
