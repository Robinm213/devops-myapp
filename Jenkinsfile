pipeline {
    agent any

    options {
        timeout(time: 60, unit: 'MINUTES')
    }

    environment {
        GIT_CREDENTIALS = 'github-creds'   // <-- use the Jenkins credential id you added
    }

    stages {
        stage('Checkout Code') {
            steps {
                // Explicit checkout using the correct credentials id
                git branch: 'main',
                    credentialsId: "${GIT_CREDENTIALS}",
                    url: 'https://github.com/Robinm213/devops-myapp.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                // disable BuildKit for compatibility with your environment
                sh '''
                export DOCKER_BUILDKIT=0
                docker build -t myapp:latest .
                '''
            }
        }

        stage('Stop Old Container') {
            steps {
                sh 'docker rm -f myapp-container || true'
            }
        }

        stage('Run New Container') {
            steps {
                sh 'docker run -d --restart unless-stopped -p 8501:8501 --name myapp-container myapp:latest'
            }
        }
    }
}
