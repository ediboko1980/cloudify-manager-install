set -eux
mkdir ~/.ssh
cp /tmp/cloudify-manager-install/premium.pem ~/.ssh/id_rsa
chmod 0400 ~/.ssh/id_rsa
ssh-keyscan github.com >> ~/.ssh/known_hosts
rm ~/rpm -fr
cp /tmp/cloudify-manager-install ~/rpm -fr
pushd ~/rpm/rpms
    ~/rpm/packaging/fetch_requirements --edition premium
popd
pushd ~/rpm
    source packaging/version_info
    rpmbuild -D "CLOUDIFY_VERSION ${CLOUDIFY_VERSION}" -D "CLOUDIFY_PACKAGE_RELEASE ${CLOUDIFY_PACKAGE_RELEASE}" -bb packaging/install_rpm.spec
    cp x86_64/*.rpm /tmp/cloudify-manager-install 
popd