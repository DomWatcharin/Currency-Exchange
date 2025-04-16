DOCKER_COMPOSE = docker-compose
DOCKER_IMAGE = CurrencyExchangeAPI
DOCKER_TAG = latest
ENV_FILE ?= .env.development

.PHONY: help build up down logs test migrate requirements restart set-env-prod set-env-dev

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

set-env-prod:
	@echo "ENV_FILE=.env.production" > .env
	@echo "Environment set to production. Run 'make up' to start the containers."

set-env-dev:
	@echo "ENV_FILE=.env.development" > .env
	@echo "Environment set to development. Run 'make up' to start the containers."

build:
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) build

up:
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) up -d

down:
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) down --remove-orphans

logs:
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) logs -f

test:
	. .venv/bin/activate && pytest

migrate:
	alembic upgrade head

requirements:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements.txt

restart:
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) down
	@export $(shell cat .env | xargs) && $(DOCKER_COMPOSE) --env-file $(ENV_FILE) up -d
