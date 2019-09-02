FROM docker-daemon:centos:7

RUN yum install -y deltarpm
RUN yum install -y epel-release
RUN yum install -y cronie
RUN yum install -y initscripts sudo openssh openssh-clients openssh-server \
	systemd-sysv openssl-1.0.2k libselinux-utils logrotate java-headless \
    python-setuptools python-backports python-backports-ssl_match_hostname which
RUN ssh-keygen -A

CMD ["/sbin/init"]