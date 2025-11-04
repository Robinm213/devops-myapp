pipeline {
    agent any

    options {
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        DOCKER_BUILDKIT = "1"
    }

    environment {
        GIT_CREDENTIALS = 'Robinm213'   // <-- Jenkins credential ID
    }

    stages {

        stage('Checkout Code') {
            steps {
                git branch: 'main',
                    credentialsId: "${GIT_CREDENTIALS}",
                    url: 'https://github.com/Robinm213/devops-myapp.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t myapp:latest .'
            }
        }

        stage('Stop Old Container') {
            steps {
                sh 'docker rm -f myapp-container || true'
            }
        }

        stage('Run New Container') {
            steps {
                sh 'docker run -d -p 8501:8501 --name myapp-container myapp:latest'
            }
        }
    }
}
