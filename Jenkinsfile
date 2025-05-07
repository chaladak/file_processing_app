this.runJob()


void runJob() {
    Map<String, Object> args = [
            runMode               : '',
            operatorRepoBranchName: '',
            version               : '',
            binaries              : ['linux-amd64', 'darwin-amd64', 'windows-amd64'],
    ]

    nodeLib.node(label: '', time: 180) {
        withCSIDevkitContainer() {
            stages {
                stage('Checkout') {
                    steps {
                        checkout scm
                    }
                }
                
                stage('Build Docker Images') {
                    steps {
                        script {
                            withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                                sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_REGISTRY}"
                            }
                            
                            sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG} ./api_service"
                            sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG} ./processor_service"
                            sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG} ./notification_service"
                        }
                    }
                }

            }
        }
    }
}

void withCSIDevkitContainer(Closure body) {
    withDockerContainer(args: '--network host --ipc=host -v /root:/root -v /etc/resolv.conf:/etc/resolv.conf -v /tmp:/tmp -v /var/run/docker.sock:/var/run/docker.sock -e "EUID=0" -e "EGID=0"', image: 'asdrepo.isus.emc.com:9042/csi-baremetal-devkit:latest', setRootPassword: true) {
        body()
  }
}

this