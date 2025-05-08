pipeline {
    agent {
        label 'docker-agent'
    }

    environment {
        DOCKER_REGISTRY = "docker.io"
        DOCKER_USERNAME = "achodak"
        DOCKER_CREDS = credentials('docker-credentials-id')
        PROJECT_NAME = "fileprocessing"
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        TAG = "${env.BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build Docker Images') {
            steps {
                container('docker') {
                    script {    
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                            sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_REGISTRY}"
                        }
                        
                        sh "docker build --network=host -t ${DOCKER_USERNAME}/${PROJECT_NAME}-api:${TAG} ./api_service"
                        sh "docker build --network=host -t ${DOCKER_USERNAME}/${PROJECT_NAME}-processor:${TAG} ./processor_service"
                        sh "docker build --network=host -t ${DOCKER_USERNAME}/${PROJECT_NAME}-notifier:${TAG} ./notification_service"
                    }
                }
            }
        }
        
        stage('Push Docker Images') {
            steps {
                container('docker') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                            sh "echo ${PASSWORD} | docker login ${DOCKER_REGISTRY} -u ${USERNAME} --password-stdin"
                        }
                        
                        sh "docker push ${DOCKER_USERNAME}/${PROJECT_NAME}-api:${TAG}"
                        sh "docker push ${DOCKER_USERNAME}/${PROJECT_NAME}-processor:${TAG}"
                        sh "docker push ${DOCKER_USERNAME}/${PROJECT_NAME}-notifier:${TAG}"
                    }
                }
            }
        }
    }
}