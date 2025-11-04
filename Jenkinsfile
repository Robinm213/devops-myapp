pipeline {
    agent any

    stages {
        stage('Deploy') {
            steps {
                sh '''
                docker stop devops-container || true
                docker rm devops-container || true
                docker build -t devops-myapp .
                docker run -d -p 8501:8501 --name devops-container devops-myapp
                '''
            }
        }
    }
}

