import os
import pytest
import requests
import docker
import time
from typing import Generator

# Test configuration
TEST_PORT = "8123"
TEST_CONTAINER_NAME = "vanna-test"

@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    return docker.from_env()

@pytest.fixture(scope="session")
def test_container(docker_client: docker.DockerClient) -> Generator[docker.models.containers.Container, None, None]:
    # Build the image
    image, _ = docker_client.images.build(
        path=os.path.join(os.path.dirname(__file__), ".."),
        dockerfile="Dockerfile",
        tag="vanna-test:latest"
    )
    
    # Run the container
    container = docker_client.containers.run(
        "vanna-test:latest",
        name=TEST_CONTAINER_NAME,
        environment={
            "VANNA_PORT": TEST_PORT,
            "VANNA_API_KEY": "test-key",
            "VANNA_MODEL": "gpt-4",
            "VANNA_VECTOR_STORE": "chromadb"
        },
        ports={f"{TEST_PORT}/tcp": TEST_PORT},
        detach=True
    )
    
    # Wait for container to be healthy
    time.sleep(5)
    
    yield container
    
    # Cleanup
    container.stop()
    container.remove()
    docker_client.images.remove("vanna-test:latest")

def test_container_running(test_container):
    """Test if container is running"""
    container_info = test_container.attrs
    assert container_info["State"]["Status"] == "running"

def test_health_check(test_container):
    """Test if health check endpoint is responding"""
    max_retries = 5
    retry_delay = 2
    
    for _ in range(max_retries):
        try:
            response = requests.get(f"http://localhost:{TEST_PORT}/health")
            if response.status_code == 200:
                assert True
                return
        except requests.exceptions.ConnectionError:
            time.sleep(retry_delay)
    
    assert False, "Health check endpoint not responding"

def test_environment_variables(test_container):
    """Test if environment variables are set correctly"""
    config = test_container.attrs["Config"]["Env"]
    
    required_vars = {
        "VANNA_PORT": TEST_PORT,
        "VANNA_API_KEY": "test-key",
        "VANNA_MODEL": "gpt-4",
        "VANNA_VECTOR_STORE": "chromadb"
    }
    
    for var, value in required_vars.items():
        assert f"{var}={value}" in config

def test_exposed_port(test_container):
    """Test if port is exposed correctly"""
    ports = test_container.attrs["NetworkSettings"]["Ports"]
    assert f"{TEST_PORT}/tcp" in ports

def test_file_permissions(test_container):
    """Test if file permissions are set correctly"""
    # Check data directory permissions
    exit_code, output = test_container.exec_run(
        "ls -l /app/data",
        user="vanna"
    )
    assert exit_code == 0

    # Check logs directory permissions
    exit_code, output = test_container.exec_run(
        "ls -l /app/logs",
        user="vanna"
    )
    assert exit_code == 0

def test_non_root_user(test_container):
    """Test if container is running as non-root user"""
    exit_code, output = test_container.exec_run("whoami")
    assert output.decode().strip() == "vanna" 