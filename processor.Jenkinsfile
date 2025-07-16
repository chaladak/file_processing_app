pipeline {
    agent {
        label 'docker-agent'
    }

    environment {
        DOCKER_HUB = "docker.io"
        DOCKER_REGISTRY = "achodak"
        DOCKER_CREDS = credentials('docker-credentials-id')
        KUBECONFIG = credentials('kubeconfig')
        PROJECT_NAME = "fileprocessing"
        SERVICE_NAME = "processor"
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        TAG = "${env.BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
    }

    stages {
        
        stage('Build Docker Image') {
            steps {
                container('docker') {
                    script {    
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                            sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_HUB}"
                        }
                        
                        sh "docker build --network=host -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-${SERVICE_NAME}:${TAG} ./processor_service"
                    }
                }
            }
        }

        stage('Run tests') {
            steps {
                container('docker') {
                    script {
                        sh '''
                            # Run your test commands here
                            echo "Running tests..."
                            # Example: ./run_tests.sh
                        '''
                    }
                }
            }
        }
        
        stage('Push Docker Image') {
            steps {
                container('docker') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                            sh "echo ${PASSWORD} | docker login ${DOCKER_HUB} -u ${USERNAME} --password-stdin"
                        }
                        
                        sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-${SERVICE_NAME}:${TAG}"
                    }
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                container('docker') {
                    script {
                        sh '''
                            apk add --no-cache curl
                            curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
                            chmod +x kubectl
                            mv kubectl /usr/local/bin/
                            kubectl version --client
                        '''
                        
                        sh """
                            export KUBECONFIG=${KUBECONFIG}
                            cat infra/processor.yaml | sed 's|\\\${DOCKER_REGISTRY}|${DOCKER_REGISTRY}|g' | sed 's|\\\${PROJECT_NAME}|${PROJECT_NAME}|g' | sed 's|\\\${TAG}|${TAG}|g' | kubectl apply -f -
                            kubectl -n ${PROJECT_NAME} wait --for=condition=available deployment/processor --timeout=300s
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            // Clean workspace
            cleanWs()
        }
        
        success {
            // Notify on success
            echo "Processor service deployment completed successfully!"
            echo "Deployed ${DOCKER_REGISTRY}/${PROJECT_NAME}-${SERVICE_NAME}:${TAG}"
        }
        
        failure {
            // Notify on failure
            echo "Processor service deployment failed!"
        }
    }
}