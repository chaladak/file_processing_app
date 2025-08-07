pipeline {
    agent {
        label 'docker-agent'
    }

    environment {
        KUBECONFIG = credentials('kubeconfig')
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        TAG = "${env.BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
    }

    stages {
        stage('Build Docker Images') {
            steps {
                container('docker') {
                    script {
                        apk add --no-cache make
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                            sh """
                                export DOCKER_USERNAME=${DOCKER_USERNAME}
                                export DOCKER_PASSWORD=${DOCKER_PASSWORD}
                                export BUILD_NUMBER=${BUILD_NUMBER}
                                export TAG=${TAG}
                                make build
                            """
                        }
                    }
                }
            }
        }

        stage('Run Integration Tests') {
            steps {
                container('docker') {
                    script {
                        sh """
                            export BUILD_NUMBER=${BUILD_NUMBER}
                            export TAG=${TAG}
                            make test
                        """
                    }
                }
            }
            post {
                always {
                    sh "make test-cleanup || true"
                }
            }
        }

        stage('Push Docker Images') {
            steps {
                container('docker') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'DOCKER_USERNAME', passwordVariable: 'DOCKER_PASSWORD')]) {
                            sh """
                                export DOCKER_USERNAME=${DOCKER_USERNAME}
                                export DOCKER_PASSWORD=${DOCKER_PASSWORD}
                                export BUILD_NUMBER=${BUILD_NUMBER}
                                export TAG=${TAG}
                                make push
                            """
                        }
                    }
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                container('docker') {
                    script {
                        sh """
                            export KUBECONFIG=${KUBECONFIG}
                            export BUILD_NUMBER=${BUILD_NUMBER}
                            export TAG=${TAG}
                            make deploy
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            sh "make clean || true"
            cleanWs()
        }
        
        success {
            echo "Deployment completed successfully!"
        }
        
        failure {
            echo "Deployment failed!"
        }
    }
}