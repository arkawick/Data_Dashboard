pipeline {
    agent any

    environment {
        MONGO_URI   = "mongodb://localhost:27017/"
        DB_NAME     = "test_db"
        NEO4J_URI   = "bolt://localhost:7687"
        NEO4J_USER  = "neo4j"
        PYTHON      = "python"
        PIP         = "pip"
    }

    triggers {
        cron("H 2 * * *")   // Nightly at 2am
    }

    options {
        timeout(time: 60, unit: "MINUTES")
        buildDiscarder(logRotator(numToKeepStr: "10"))
        timestamps()
    }

    stages {

        stage("Checkout") {
            steps {
                checkout scm
                echo "Branch: ${env.BRANCH_NAME}"
            }
        }

        stage("Install Dependencies") {
            steps {
                sh "${PIP} install ruff pytest pymongo networkx fastapi httpx uvicorn pydantic prometheus-client anthropic"
            }
        }

        stage("Lint") {
            steps {
                sh "ruff check . --ignore E501,E402,W291 --exclude __pycache__"
            }
        }

        stage("Test") {
            steps {
                sh "${PYTHON} -m pytest tests/ -v --tb=short --junitxml=test-results.xml"
            }
            post {
                always {
                    junit "test-results.xml"
                }
            }
        }

        stage("Refresh Data") {
            when { branch "main" }
            steps {
                sh "${PYTHON} generate_data.py"
            }
        }

        stage("Build Graph") {
            when { branch "main" }
            steps {
                sh "${PYTHON} graphrag/build_graph.py"
                sh "${PYTHON} graphrag/chunk_graph.py"
            }
        }

        stage("Embed Chunks") {
            when { branch "main" }
            steps {
                script {
                    try {
                        sh "${PIP} install faiss-cpu sentence-transformers"
                        sh "${PYTHON} graphrag/embed_chunks.py"
                    } catch (Exception e) {
                        echo "Embed step skipped or failed: ${e.getMessage()}"
                    }
                }
            }
        }

        stage("Load Neo4j") {
            when {
                allOf {
                    branch "main"
                    environment name: "NEO4J_AVAILABLE", value: "true"
                }
            }
            steps {
                sh "${PYTHON} graphrag/load_neo4j.py"
            }
        }

        stage("Docker Build") {
            when { branch "main" }
            steps {
                sh "docker compose build --no-cache"
            }
        }

        stage("Docker Deploy") {
            when { branch "main" }
            steps {
                sh "docker compose up -d"
            }
        }

        stage("Smoke Test") {
            when { branch "main" }
            steps {
                sh "sleep 10"
                sh "curl -f http://localhost:8000/ || (docker compose logs django && exit 1)"
                sh "curl -f http://localhost:8001/health || (docker compose logs fastapi && exit 1)"
            }
        }

        stage("Validate Graph") {
            when { branch "main" }
            steps {
                sh """
                    ${PYTHON} -c \"
import json, os
g = json.load(open('graphrag/graph.json'))
s = g.get('stats', {})
nodes = s.get('nodes', 0)
edges = s.get('edges', 0)
assert nodes >= 100, f'Node count too low: {nodes}'
assert edges >= 200, f'Edge count too low: {edges}'
print(f'Graph validation passed: {nodes} nodes, {edges} edges')
\"
                """
            }
        }

    }

    post {
        success {
            echo "Pipeline passed. Dashboard is running."
        }
        failure {
            echo "Pipeline FAILED. Check console output above."
            sh "docker compose logs --tail=50 || true"
        }
        always {
            echo "Pipeline finished."
        }
    }
}
