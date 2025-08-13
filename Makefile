# Variables
DOCKER_REGISTRY ?= achodak
PROJECT_NAME ?= fileprocessing
DOCKER_HUB ?= docker.io

# Service paths
API_SERVICE = api_service
PROCESSOR_SERVICE = processor_service
NOTIFIER_SERVICE = notification_service

# Docker compose files
INTEGRATION_COMPOSE = tests/integration/docker-compose.yml

.PHONY: build test push deploy clean docker-login install-deps

install-deps:
	@apk add --no-cache curl
	@curl -LO "https://dl.k8s.io/release/$$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
	@chmod +x kubectl
	@mv kubectl /usr/local/bin/
	@kubectl version --client

docker-login:
	@echo "$(DOCKER_PASSWORD)" | docker login $(DOCKER_HUB) -u "$(DOCKER_USERNAME)" --password-stdin

build:
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(TAG) ./$(API_SERVICE)
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-processor:$(TAG) ./$(PROCESSOR_SERVICE)
	docker build -t $(DOCKER_REGISTRY)/$(PROJECT_NAME)-notifier:$(TAG) ./$(NOTIFIER_SERVICE)

test-setup:
	-docker-compose -f $(INTEGRATION_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	-docker container prune -f 2>/dev/null || true
	-docker network prune -f 2>/dev/null || true
	-docker volume prune -f 2>/dev/null || true
	docker-compose -f $(INTEGRATION_COMPOSE) up -d --force-recreate

test-wait:
	@timeout=300; \
	elapsed=0; \
	interval=5; \
	while [ $$elapsed -lt $$timeout ]; do \
		if docker-compose -f $(INTEGRATION_COMPOSE) ps | grep -q "healthy"; then \
			health_count=$$(docker-compose -f $(INTEGRATION_COMPOSE) ps | grep -c "healthy" || echo "0"); \
			if [ "$$health_count" -ge "2" ]; then \
				echo "Services are healthy"; \
				break; \
			fi; \
		fi; \
		echo "Waiting for services... ($$elapsed/$$timeout seconds)"; \
		sleep $$interval; \
		elapsed=$$((elapsed + interval)); \
	done; \
	if [ $$elapsed -ge $$timeout ]; then \
		echo "Services failed to become healthy"; \
		docker-compose -f $(INTEGRATION_COMPOSE) ps; \
		docker-compose -f $(INTEGRATION_COMPOSE) logs; \
		exit 1; \
	fi

test-run:
	@# Find the network created by docker-compose
	@NETWORK_NAME=$$(docker network ls --filter "name=integration" --format "{{.Name}}" | head -n1); \
	if [ -z "$$NETWORK_NAME" ]; then \
		echo "Error: Could not find integration network. Available networks:"; \
		docker network ls; \
		exit 1; \
	fi; \
	echo "Using network: $$NETWORK_NAME"; \
	container_id=$$(docker run -d \
		--network $$NETWORK_NAME \
		-e TESTING=true \
		-e S3_ENDPOINT=http://minio:9000 \
		-e S3_ACCESS_KEY=minioadmin \
		-e S3_SECRET_KEY=minioadmin \
		-e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/%2F \
		-e DATABASE_URL=sqlite:///:memory: \
		-e NFS_PATH=/tmp \
		-e PYTHONPATH=/app \
		python:3.12-slim \
		sleep 600); \
	\
	echo "Test container ID: $$container_id"; \
	docker exec $$container_id mkdir -p /app /app/tests; \
	docker cp ./$(API_SERVICE)/. $$container_id:/app/$(API_SERVICE)/; \
	docker cp ./$(PROCESSOR_SERVICE)/. $$container_id:/app/$(PROCESSOR_SERVICE)/; \
	docker cp ./$(NOTIFIER_SERVICE)/. $$container_id:/app/$(NOTIFIER_SERVICE)/; \
	docker cp ./tests/integration/. $$container_id:/app/tests/integration/; \
	\
	docker exec $$container_id touch /app/$(API_SERVICE)/__init__.py; \
	docker exec $$container_id touch /app/$(PROCESSOR_SERVICE)/__init__.py; \
	docker exec $$container_id touch /app/$(NOTIFIER_SERVICE)/__init__.py; \
	\
	test_exit_code=0; \
	docker exec $$container_id /bin/bash -c " \
		set -e; \
		cd /app; \
		apt-get update && apt-get install -y gcc; \
		pip install --no-cache-dir -r tests/integration/requirements.txt; \
		pip install --no-cache-dir -r $(API_SERVICE)/requirements.txt; \
		pip install --no-cache-dir -r $(PROCESSOR_SERVICE)/requirements.txt; \
		pip install --no-cache-dir -r $(NOTIFIER_SERVICE)/requirements.txt; \
		export PYTHONPATH=/app:/app/$(API_SERVICE):/app/$(PROCESSOR_SERVICE):/app/$(NOTIFIER_SERVICE):\$$PYTHONPATH; \
		python -m pytest tests/integration/test_integration.py -v --tb=short \
	" || test_exit_code=$$?; \
	\
	echo "Cleaning up test container: $$container_id"; \
	docker rm -f $$container_id; \
	\
	if [ $$test_exit_code -eq 0 ]; then \
		echo "Integration tests PASSED"; \
	else \
		echo "Integration tests FAILED"; \
		exit $$test_exit_code; \
	fi

test-cleanup:
	-docker-compose -f $(INTEGRATION_COMPOSE) down -v 2>/dev/null || true

test: test-setup test-wait test-run test-cleanup

push: docker-login
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-api:$(TAG)
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-processor:$(TAG)
	docker push $(DOCKER_REGISTRY)/$(PROJECT_NAME)-notifier:$(TAG)

k8s-apply-infrastructure:
	@for file in namespace configmap secret nfs-pv postgres rabbitmq minio; do \
		cat k8s/$$file.yaml | sed 's|\$${PROJECT_NAME}|$(PROJECT_NAME)|g' | kubectl apply -f -; \
	done

k8s-wait-infrastructure:
	kubectl -n $(PROJECT_NAME) wait --for=condition=ready pod -l app=postgres --timeout=120s
	kubectl -n $(PROJECT_NAME) wait --for=condition=ready pod -l app=rabbitmq --timeout=120s
	kubectl -n $(PROJECT_NAME) wait --for=condition=ready pod -l app=minio --timeout=120s

k8s-apply-services:
	@for service in api processor notifier; do \
		cat k8s/$$service.yaml | \
			sed 's|\$${DOCKER_REGISTRY}|$(DOCKER_REGISTRY)|g' | \
			sed 's|\$${PROJECT_NAME}|$(PROJECT_NAME)|g' | \
			sed 's|\$${TAG}|$(TAG)|g' | \
			kubectl apply -f -; \
	done

k8s-apply-ingress:
	cat k8s/ingress.yaml | sed 's|\$${PROJECT_NAME}|$(PROJECT_NAME)|g' | kubectl apply -f -

deploy: install-deps k8s-apply-infrastructure k8s-wait-infrastructure k8s-apply-services k8s-apply-ingress

clean:
	-docker-compose -f $(INTEGRATION_COMPOSE) down -v --remove-orphans 2>/dev/null || true
	-docker container prune -f 2>/dev/null || true
	-docker image prune -f 2>/dev/null || true
	-docker network prune -f 2>/dev/null || true
	-docker volume prune -f 2>/dev/null || true