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

        stage('Run Integration Tests') {
            steps {
                container('docker') {
                    script {
                        sh '''
                            cd ${WORKSPACE}
                            
                            docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml up -d --force-recreate

                            echo "Waiting for services to be healthy..."
                            timeout=300  # 5 minutes
                            elapsed=0
                            interval=5

                            while [ $elapsed -lt $timeout ]; do
                                if docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml ps | grep -q "healthy"; then
                                    health_count=$(docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml ps | grep -c "healthy")
                                    if [ $health_count -eq 2 ]; then
                                        echo "All services are healthy!"
                                        break
                                    fi
                                fi
                                echo "Waiting for services to be healthy... ($elapsed/$timeout seconds)"
                                sleep $interval
                                elapsed=$((elapsed + interval))
                            done

                            if [ $elapsed -ge $timeout ]; then
                                echo "ERROR: Services failed to become healthy within $timeout seconds"
                                docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml ps
                                docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml logs
                                exit 1
                            fi

                            echo "Starting test container..."
                            container_id=$(docker run -d \
                                --network host \
                                -e TESTING=true \
                                -e S3_ENDPOINT=http://localhost:9000 \
                                -e S3_ACCESS_KEY=minioadmin \
                                -e S3_SECRET_KEY=minioadmin \
                                -e RABBITMQ_URL=amqp://guest:guest@localhost:5672/%2F \
                                -e DATABASE_URL=sqlite:///:memory: \
                                -e NFS_PATH=/tmp \
                                -e PYTHONPATH=/app \
                                python:3.12-slim \
                                sleep 600)

                            docker exec $container_id mkdir -p /app /app/tests
                            docker cp ${WORKSPACE}/api_service/. $container_id:/app/api_service/
                            docker cp ${WORKSPACE}/processor_service/. $container_id:/app/processor_service/
                            docker cp ${WORKSPACE}/notification_service/. $container_id:/app/notification_service/
                            docker cp ${WORKSPACE}/tests/integration/. $container_id:/app/tests/integration/

                            docker exec $container_id touch /app/api_service/__init__.py
                            docker exec $container_id touch /app/processor_service/__init__.py
                            docker exec $container_id touch /app/notification_service/__init__.py

                            echo "Running integration tests..."
                            docker exec $container_id /bin/bash -c "
                                set -e
                                cd /app
                                
                                echo 'Installing dependencies...'
                                pip install --no-cache-dir -r tests/integration/requirements.txt
                                pip install --no-cache-dir -r api_service/requirements.txt
                                pip install --no-cache-dir -r processor_service/requirements.txt
                                pip install --no-cache-dir -r notification_service/requirements.txt
                                
                                export PYTHONPATH=/app:/app/api_service:/app/processor_service:/app/notification_service:\$PYTHONPATH
                                
                                echo 'Running integration tests...'
                                python -m pytest tests/integration/test_integration.py -v --tb=short
                            "

                            test_exit_code=$?
                            
                            docker rm -f $container_id
                            docker-compose -f ${WORKSPACE}/tests/integration/docker-compose.yml down -v

                            if [ $test_exit_code -eq 0 ]; then
                                echo "Integration tests PASSED"
                            else
                                echo "Integration tests FAILED"
                                exit $test_exit_code
                            fi
                        '''
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
                            
                            cat k8s/namespace.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/configmap.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/secret.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/nfs-pv.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/postgres.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/rabbitmq.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            cat k8s/minio.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
                            
                            # Wait for infrastructure to be ready
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=postgres --timeout=120s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=rabbitmq --timeout=120s
                            kubectl -n ${PROJECT_NAME} wait --for=condition=ready pod -l app=minio --timeout=120s
                            
                            # Apply application services with special handling for image tags
                            cat k8s/api.yaml | sed 's|\\\${DOCKER_REGISTRY}|${DOCKER_REGISTRY}|g' | sed 's|\\\${PROJECT_NAME}|${PROJECT_NAME}|g' | sed 's|\\\${TAG}|${TAG}|g' | kubectl apply -f -
                            cat k8s/processor.yaml | sed 's|\\\${DOCKER_REGISTRY}|${DOCKER_REGISTRY}|g' | sed 's|\\\${PROJECT_NAME}|${PROJECT_NAME}|g' | sed 's|\\\${TAG}|${TAG}|g' | kubectl apply -f -
                            cat k8s/notifier.yaml | sed 's|\\\${DOCKER_REGISTRY}|${DOCKER_REGISTRY}|g' | sed 's|\\\${PROJECT_NAME}|${PROJECT_NAME}|g' | sed 's|\\\${TAG}|${TAG}|g' | kubectl apply -f -

                            # Apply ingress last
                            cat k8s/ingress.yaml | sed 's|\${PROJECT_NAME}|${PROJECT_NAME}|g' | kubectl apply -f -
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
            echo "Deployment completed successfully!"
        }
        
        failure {
            echo "Deployment failed!"
        }
    }
}