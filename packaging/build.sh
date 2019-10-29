set -eux
mkdir ~/.ssh
cp /tmp/cloudify-manager-install/premium.pem ~/.ssh/id_rsa
chmod 0400 ~/.ssh/id_rsa
ssh-keyscan github.com >> ~/.ssh/known_hosts
pushd /tmp/cloudify-manager-install/rpms
    /tmp/cloudify-manager-install/packaging/fetch_requirements --edition premium
popd
rm ~/rpm -fr
ln -s /tmp/cloudify-manager-install ~/rpm
pushd /tmp/cloudify-manager-install
    source packaging/version_info
    rpmbuild -D "CLOUDIFY_VERSION ${CLOUDIFY_VERSION}" -D "CLOUDIFY_PACKAGE_RELEASE ${CLOUDIFY_PACKAGE_RELEASE}" -bb packaging/install_rpm.spec
popd
