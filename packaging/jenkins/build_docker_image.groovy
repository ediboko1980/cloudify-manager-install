pipeline {
    agent {
        node 'docker'
    }
    parameters {
        string(name: 'CLOUDIFY_TAG')
        string(name: 'RPM_BUILD_NUMBER')
        choice(name: 'IMAGE_TYPE', choices: "manager-aio\npostgresql\nrabbitmq\nmanager-worker")
    }
    stages {
        stage('Build image'){
            steps {
                script {
                    switch (params.IMAGE_TYPE) {
                        case "manager-aio":
                            config = 'config.yaml'
                            label = 'cloudify-manager-aio'
                            break
                        case "postgresql":
                            config = 'config_db.yaml'
                            label = 'cloudify-db'
                            break
                        case "rabbitmq":
                            config = 'config_queue.yaml'
                            label = 'cloudify-queue'
                            break
                        case 'manager-worker':
                            config = 'config_manager.yaml'
                            label = 'cloudify-manager-worker'
                            break
                    }
                }
                copyArtifacts(
                    projectName: 'dir_manager/_temp_build_rpm',
                    selector: params.RPM_BUILD_NUMBER ? specific(params.RPM_BUILD_NUMBER) : lastSuccessful(),
                    target: 'packaging/docker'
                )
                sh "mv packaging/docker/cloudify-manager-install*.rpm packaging/docker/cloudify-manager-install.rpm"
                sh """
                    docker build -t ${label} --build-arg config=${config} packaging/docker
                """
                sh """
                    docker image save -o cloudify-${params.IMAGE_TYPE}-docker-${params.CLOUDIFY_TAG}.tar ${label}:latest
                """

            }
            post {
                success {
                    archiveArtifacts artifacts: '*.tar', fingerprint: true
                }
                cleanup {
                    cleanWs()
                }
            }
        }
    }
}
