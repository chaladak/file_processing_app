pipeline {
    agent {
        label 'docker-agent'
    }

    environment {
        KUBECONFIG = credentials('kubeconfig')
        PROJECT_NAME = "fileprocessing"
    }

    stages {
        
        stage('Setup kubectl') {
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
        
        stage('Deploy Infrastructure') {
            steps {
                container('docker') {
                    script {
                        sh """
                            export KUBECONFIG=${KUBECONFIG}
                            
                            # Create namespace first
                            echo "Creating namespace..."
                            cat infra/namespace.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Apply configuration and secrets
                            echo "Applying ConfigMap and Secrets..."
                            cat infra/configmap.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat infra/secret.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Apply persistent volumes
                            echo "Applying Persistent Volumes..."
                            cat infra/nfs-pv.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Deploy database services
                            echo "Deploying PostgreSQL..."
                            cat infra/postgres.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Deploy message queue
                            echo "Deploying RabbitMQ..."
                            cat infra/rabbitmq.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Deploy object storage
                            echo "Deploying MinIO..."
                            cat infra/minio.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Wait for infrastructure to be ready
                            echo "Waiting for infrastructure to be ready..."
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=postgres --timeout=300s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=rabbitmq --timeout=300s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=minio --timeout=300s
                            
                            # Deploy ingress last
                            echo "Deploying Ingress..."
                            cat infra/ingress.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Verify deployment
                            echo "Verifying infrastructure deployment..."
                            kubectl -n ${PROJECT_NAME} get all
                            kubectl -n ${PROJECT_NAME} get pv,pvc
                            kubectl -n ${PROJECT_NAME} get ingress
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        
        success {
            echo "Infrastructure deployment completed successfully!"
            echo "Namespace: ${PROJECT_NAME}"
            echo "Services deployed: PostgreSQL, RabbitMQ, MinIO, Ingress"
        }
        
        failure {
            echo "Infrastructure deployment failed!"
        }
    }
}