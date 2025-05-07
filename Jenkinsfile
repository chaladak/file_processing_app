pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = "achodak"
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
                script {
                    sh "uname -a"
                    sh "cat /etc/os-release"
                    withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                        sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_REGISTRY}"
                    }
                    
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG} ./api_service"
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG} ./processor_service"
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG} ./notification_service"
                }
            }
        }
        
        stage('Push Docker Images') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                        sh "echo ${PASSWORD} | docker login ${DOCKER_REGISTRY} -u ${USERNAME} --password-stdin"
                    }
                    
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG}"
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG}"
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG}"
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                withCredentials([file(credentialsId: 'k8s-config-id', variable: 'KUBECONFIG_PATH')]) {
                    script {
                        sh """
                            export KUBECONFIG=${KUBECONFIG_PATH}
                            
                            # Ensure namespace exists
                            kubectl apply -f k8s-manifests/namespace.yaml
                            
                            # Apply infrastructure resources
                            kubectl apply -f k8s-manifests/configmap.yaml
                            kubectl apply -f k8s-manifests/secret.yaml
                            kubectl apply -f k8s-manifests/nfs-pv.yaml
                            kubectl apply -f k8s-manifests/postgres.yaml
                            kubectl apply -f k8s-manifests/rabbitmq.yaml
                            kubectl apply -f k8s-manifests/minio.yaml
                            
                            # Wait for infrastructure to be ready
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=postgres --timeout=120s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=rabbitmq --timeout=120s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=minio --timeout=120s
                            
                            # Deploy application services
                            kubectl apply -f k8s-manifests/api.yaml
                            kubectl apply -f k8s-manifests/processor.yaml
                            kubectl apply -f k8s-manifests/notifier.yaml
                            
                            # Apply ingress
                            kubectl apply -f k8s-manifests/ingress.yaml
                        """
                    }
                }
            }
        }
        
        stage('Final Cleanup') {
            steps {
                echo "Cleaning up workspace"
                cleanWs()
            }
        }
    }
    
    post {
        success {
            echo "Deployment completed successfully!"
        }
        failure {
            echo "Deployment failed!"
        }
    }
}
