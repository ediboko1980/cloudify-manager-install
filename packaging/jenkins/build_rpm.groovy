pipeline {
    agent {
        dockerfile {
            dir 'packaging/jenkins/rpm_builder'
            args '-u root -v /var/lib/jenkins/jobs/credentials.sh:/credentials.sh:ro'
        }
    }
    parameters {
        string(name: 'VERSION')
        string(name: 'PRERELEASE')
        string(name: 'BRANCH', defaultValue: 'master')
        string(name: 'EDITION', defaultValue: 'premium')
    }
    stages {
        stage('Download requirements'){
            steps {
                sh """
                    ln -s "${WORKSPACE}" ~/rpmbuild/SOURCES
                """
                sh """
                    source /credentials.sh > /dev/null 2>&1 &&
                    mkdir rpms
                    pushd 'rpms'
                        ../packaging/fetch_requirements -b ${params.BRANCH} --edition ${params.EDITION}
                    popd
                """
            }
        }
        stage('Build the manager RPM'){
            steps {
                sh """
                    rpmbuild -D "CLOUDIFY_VERSION ${params.VERSION}" -D "CLOUDIFY_PACKAGE_RELEASE ${params.PRERELEASE}" -bb packaging/install_rpm.spec
                """
                sh """
                    mv ~/rpmbuild/RPMS/x86_64/*.rpm "${WORKSPACE}"
                """
            }
            post {
                success {
                    archiveArtifacts artifacts: '*.rpm', fingerprint: true
                }
                cleanup {
                    cleanWs()
                }
            }
        }
    }
}
