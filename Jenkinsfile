pipeline {
    agent any
    
    environment {
        DOCKER_REGISTRY = "achodak"
        DOCKER_CREDS = credentials('docker-credentials-id')
        PROJECT_NAME = "fileprocessing"
        GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
        TAG = "${env.BUILD_NUMBER}-${GIT_COMMIT_SHORT}"
        USERNAME = credentials('ssh-username-id')  // Jenkins credentials ID for SSH username
        PASSWORD = credentials('ssh-password-id')  // Jenkins credentials ID for SSH password
        E2E_VM_SERVICE_NODE_IP = "100.80.77.191"  // Replace with your node IP
        RANCHER_CONFIG_PATH = "/etc/rancher/rke2/rke2.yaml"  // Destination path for kubeconfig
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install sshpass') {
            steps {
                sh """
                    # Detect package manager
                    if command -v apt-get &> /dev/null; then
                        sudo apt-get update && sudo apt-get install -y sshpass
                    elif command -v yum &> /dev/null; then
                        sudo yum install -y epel-release && sudo yum install -y sshpass
                    elif command -v apk &> /dev/null; then
                        sudo apk add --no-cache sshpass
                    else
                        echo "Unsupported OS"
                        exit 1
                    fi
                """
            }
        }

        stage('Copy Kubeconfig and Set Up Tunnel') {    
            steps {    
                script {
                    sh """
                        echo "Copying kubeconfig..."
                        
                        sshpass -p '${PASSWORD}' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                        ${USERNAME}@${E2E_VM_SERVICE_NODE_IP}:/etc/rancher/rke2/rke2.yaml ${env.WORKSPACE_CONFIG_PATH} || {
                            echo "Error: Failed to copy rke2.yaml"; exit 1;
                        }
                        
                        chmod 600 ${env.WORKSPACE_CONFIG_PATH} || {
                            echo "Error: Failed to set permissions for rke2.yaml"; exit 1;
                        }
                        
                        export KUBECONFIG=${env.WORKSPACE_CONFIG_PATH}
                        
                        echo "Opening SSH tunnel to node VM..."
                        sshpass -p "${PASSWORD}" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                        -L 6443:localhost:6443 -N -f -l "${USERNAME}" ${E2E_VM_SERVICE_NODE_IP} || {
                            echo "Error: Failed to establish SSH tunnel"; exit 1;
                        }
                        echo "Testing kubectl connection..."
                        kubectl get nodes
                    """
                }
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
        
        stage('Push Docker Images') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
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
