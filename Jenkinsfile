pipeline {
    agent any

    stages {

        stage('Clone repo') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t myapp:latest .'
            }
        }

        stage('Stop old container') {
            steps {
                sh '''
                if [ $(docker ps -q -f name=myapp-container) ]; then
                    docker stop myapp-container
                    docker rm myapp-container
                fi
                '''
            }
        }

        stage('Run new container') {
            steps {
                sh 'docker run -d -p 8501:8501 --name myapp-container myapp:latest'
            }
        }
    }
}
