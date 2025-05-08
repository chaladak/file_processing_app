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
                            sh "docker login -u ${USERNAME} -p ${PASSWORD} ${DOCKER_HUB}"
                        }
                        
                        sh "docker build --network=host -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG} ./api_service"
                        sh "docker build --network=host -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG} ./processor_service"
                        sh "docker build --network=host -t ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG} ./notification_service"
                    }
                }
            }
        }
        
        stage('Push Docker Images') {
            steps {
                container('docker') {
                    script {
                        withCredentials([usernamePassword(credentialsId: 'docker-credentials-id', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                            sh "echo ${PASSWORD} | docker login ${DOCKER_HUB} -u ${USERNAME} --password-stdin"
                        }
                        
                        sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG}"
                        sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG}"
                        sh "docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG}"
                    }
                }
            }
        }
        stage('Deploy to Kubernetes') {
            steps {
                script {
                    // Apply Kubernetes manifests with variable substitution
                    sh """
                        envsubst --version
                        export KUBECONFIG=${KUBECONFIG}
                        
                        # Create namespace first
                        envsubst < k8s/namespace.yaml | kubectl apply -f -
                        
                        # Apply other resources with variable substitution
                        envsubst < k8s/configmap.yaml | kubectl apply -f -
                        envsubst < k8s/secret.yaml | kubectl apply -f -
                        envsubst < k8s/nfs-pv.yaml | kubectl apply -f -
                        envsubst < k8s/postgres.yaml | kubectl apply -f -
                        envsubst < k8s/rabbitmq.yaml | kubectl apply -f -
                        envsubst < k8s/minio.yaml | kubectl apply -f -
                        
                        # Wait for infrastructure to be ready
                        kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=postgres --timeout=120s
                        kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=rabbitmq --timeout=120s
                        kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=minio --timeout=120s
                        
                        # Apply application services with special handling for image tags
                        cat k8s/api.yaml | sed 's|image:.*fileprocessing-api:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-api:${TAG}|g' | envsubst | kubectl apply -f -
                        cat k8s/processor.yaml | sed 's|image:.*fileprocessing-processor:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-processor:${TAG}|g' | envsubst | kubectl apply -f -
                        cat k8s/notifier.yaml | sed 's|image:.*fileprocessing-notifier:.*|image: ${DOCKER_REGISTRY}/${PROJECT_NAME}-notifier:${TAG}|g' | envsubst | kubectl apply -f -
                        
                        # Apply ingress last
                        envsubst < k8s/ingress.yaml | kubectl apply -f -
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