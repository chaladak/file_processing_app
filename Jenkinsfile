pipeline {
    agent any
    
    environment {
        // Set up environment variables
        DOCKER_REGISTRY = "achodak" // Replace with your registry
        DOCKER_CREDS = credentials('dockerhub-creds') // Jenkins credentials ID for Docker registry
        KUBECONFIG = credentials('k8s-config-id') // Jenkins credentials ID for Kubernetes config
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
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                        sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_REGISTRY}"
                    }
                    // Build the Docker images
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG} ./api_service"
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG} ./processor_service"
                    sh "docker build -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG} ./notification_service"
                }
            }
        }
        
        stage('Push Docker Images') {
            steps {
                script {
                    // Login to Docker registry
                    sh "echo ${DOCKER_CREDS_PSW} | docker login ${DOCKER_REGISTRY} -u ${DOCKER_CREDS_USR} --password-stdin"
                    
                    // Push the Docker images
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG}"
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG}"
                    sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG}"
                }
            }
        }
        
        stage('Update Kubernetes Manifests') {
            steps {
                script {
                    // Update image tags in existing YAML files
                    sh """
                        # Update API service image
                        sed -i 's|image:.*api:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG}|g' k8s/api.yaml
                        
                        # Update Processor service image
                        sed -i 's|image:.*processor:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG}|g' k8s/processor.yaml
                        
                        # Update Notifier service image
                        sed -i 's|image:.*notifier:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG}|g' k8s/notifier.yaml
                    """
                }
            }
        }
        
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    // Apply Kubernetes manifests
                    sh """
                        export KUBECONFIG=${KUBECONFIG}
                        
                        # Create namespace first
                        kubectl apply -f k8s-manifests/namespace.yaml
                        
                        # Apply other resources
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
                        
                        # Apply ingress last
                        kubectl apply -f k8s-manifests/ingress.yaml
                    """
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
            echo "Deployment completed successfully!"
        }
        
        failure {
            // Notify on failure
            echo "Deployment failed!"
        }
    }
}