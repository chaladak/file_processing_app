pipeline {
    agent {
        label 'docker-agent'
    }
    stages {
        stage('Build') {
            steps {
                container('docker') {
                    sh 'docker version'
                    sh 'docker ps'
                    // Your Docker commands here
                }
            }
        }
    }
}