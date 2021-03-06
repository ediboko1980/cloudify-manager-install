%define _venv /opt/cloudify/cfy_manager
%define __python %_venv/bin/python
%define __find_provides %{nil}
%define __find_requires %{nil}
%define _use_internal_dependency_generator 0

%define _source_payload w0.gzdio
%define _binary_payload w0.gzdio

Name:           cloudify-manager-install
Version:        %{CLOUDIFY_VERSION}
Release:        %{CLOUDIFY_PACKAGE_RELEASE}%{?dist}
Summary:        Cloudify Manager installer
Group:          Applications/Multimedia
License:        Apache 2.0
URL:            https://github.com/cloudify-cosmo/cloudify-manager-install
Vendor:         Cloudify Platform Ltd.
Packager:       Cloudify Platform Ltd.

BuildRequires:  python3 >= 3.6, python3-devel >= 3.6, createrepo, gcc
Requires:       python3 >= 3.6
Requires(pre):  shadow-utils

%description
Cloudify Manager installer.

%build
mkdir -p $(dirname %_venv)
python3 -m venv %_venv
%_venv/bin/pip install ${RPM_SOURCE_DIR}

%install
mkdir %{buildroot}/opt
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/etc/cloudify
mkdir -p %{buildroot}/opt/cloudify
cp ${RPM_SOURCE_DIR}/config.yaml %{buildroot}/etc/cloudify/config.yaml
cp ${RPM_SOURCE_DIR}/rpms %{buildroot}/opt/cloudify/sources -Lfr
cp -R ${RPM_SOURCE_DIR}/packaging/files/* %{buildroot}

mv %_venv %{buildroot}%_venv
ln -s %_venv/bin/cfy_manager %{buildroot}/usr/bin/cfy_manager
ln -s %_venv/bin/supervisorctl %{buildroot}/usr/bin/supervisorctl
ln -s %_venv/bin/supervisord %{buildroot}/usr/bin/supervisord

/bin/createrepo %{buildroot}/opt/cloudify/sources
mkdir -p %{buildroot}/etc/yum.repos.d/
cp ${RPM_SOURCE_DIR}/packaging/localrepo %{buildroot}/etc/yum.repos.d/Cloudify-Local.repo
mkdir -p %{buildroot}/var/log/cloudify

%pre
ver=`cat /etc/redhat-release | grep -o 'release.*' | cut -f2 -d\ | cut -b 1-3`
min_ver=7.6
if (( $(awk 'BEGIN {print ("'$ver'"<"'$min_ver'")}') )); then
    >&2 echo "[ERROR] OS version earlier than $min_ver, exiting."
    exit 1;
fi

groupadd -fr cfyuser
getent passwd cfyuser >/dev/null || useradd -r -g cfyuser -d /etc/cloudify -s /sbin/nologin cfyuser
groupadd -fr rabbitmq
usermod -aG rabbitmq cfyuser

%post
echo "
###########################################################################
Cloudify installer is ready!
To install Cloudify Manager, run:
cfy_manager install --private-ip <PRIVATE_IP> --public-ip <PUBLIC_IP>
(Use cfy_manager -h for a full list of options)

You can specify more installation settings in /etc/cloudify/config.yaml. If you
specify the public and private IP addresses in the config.yaml file, run:
cfy_manager install
###########################################################################
"

%files
/usr/bin/cfy_manager
/opt/cloudify
%attr(755,cfyuser,cfyuser) /etc/cloudify
%attr(660,root,wheel) %config(noreplace) /etc/cloudify/config.yaml
/etc/yum.repos.d/Cloudify-Local.repo
/usr/lib/systemd/system/supervisord.service
/etc/supervisord.conf
/usr/bin/supervisorctl
/usr/bin/supervisord
%attr(755,cfyuser,cfyuser) /var/log/cloudify
