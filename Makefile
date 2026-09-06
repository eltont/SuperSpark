SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export PATH := $(HOME)/.local/bin:$(PATH)
export JAVA_HOME ?= $(HOME)/.local/opt/jdk-17
export SUPERSPARK_ROOT := $(ROOT)

ARCH ?= arm64
MODE ?= baseline
PROFILE ?= local
SIZE ?= tiny
NAME ?= filter_project
CONFIG ?=

LOG_DIR := $(ROOT)/artifacts/logs
REPORT_DIR := $(ROOT)/artifacts/reports

.PHONY: help doctor lock-versions check-updates update-versions bootstrap \
	scenarios-list scenario scenarios build smoke local-up local-test \
	bench report package validate-k8s deploy-k8s package-yarn validate-yarn \
	local-down test-airflow

help:
	@printf '%s\n' \
	  'SuperSpark targets:' \
	  '  make doctor | lock-versions | check-updates | update-versions' \
	  '  make bootstrap | local-up | local-down | local-test' \
	  '  make smoke MODE=baseline|native' \
	  '  make scenarios-list | scenario NAME=... MODE=... | scenarios' \
	  '  make build ARCH=arm64|amd64 | package ARCH=...' \
	  '  make bench PROFILE=local MODE=... | report' \
	  '  make validate-k8s CONFIG=... | deploy-k8s CONFIG=...' \
	  '  make package-yarn CONFIG=... | validate-yarn CONFIG=...' \
	  '  make test-airflow'

doctor:
	@mkdir -p "$(LOG_DIR)"
	@$(ROOT)/scripts/bootstrap/doctor.sh 2>&1 | tee "$(LOG_DIR)/doctor.log"
	@echo "Logs: $(LOG_DIR)/doctor.log"

lock-versions:
	@$(ROOT)/scripts/bootstrap/lock_versions.sh 2>&1 | tee "$(LOG_DIR)/lock-versions.log"
	@echo "Logs: $(LOG_DIR)/lock-versions.log"

check-updates:
	@$(ROOT)/scripts/bootstrap/check_updates.sh 2>&1 | tee "$(LOG_DIR)/check-updates.log"
	@echo "Logs: $(LOG_DIR)/check-updates.log"

update-versions:
	@echo "Refusing automatic mutation without explicit confirmation file."
	@echo "Create artifacts/ALLOW_UPDATE_VERSIONS then re-run, or edit versions.lock.yaml deliberately."
	@exit 1

bootstrap:
	@mkdir -p "$(LOG_DIR)"
	@$(ROOT)/scripts/bootstrap/bootstrap.sh 2>&1 | tee "$(LOG_DIR)/bootstrap.log"
	@echo "Logs: $(LOG_DIR)/bootstrap.log"

scenarios-list:
	@$(ROOT)/runner/bin/superspark scenarios-list

scenario:
	@$(ROOT)/runner/bin/superspark scenario --name "$(NAME)" --mode "$(MODE)" --profile "$(PROFILE)" --size "$(SIZE)"

scenarios:
	@$(ROOT)/runner/bin/superspark scenarios --profile "$(PROFILE)" --size "$(SIZE)"

build:
	@$(ROOT)/scripts/bootstrap/build_images.sh --arch "$(ARCH)" 2>&1 | tee "$(LOG_DIR)/build-$(ARCH).log"
	@echo "Logs: $(LOG_DIR)/build-$(ARCH).log"

smoke:
	@$(ROOT)/runner/bin/superspark smoke --mode "$(MODE)" 2>&1 | tee "$(LOG_DIR)/smoke-$(MODE).log"
	@echo "Logs: $(LOG_DIR)/smoke-$(MODE).log"

local-up:
	@$(ROOT)/scripts/bootstrap/local_up.sh 2>&1 | tee "$(LOG_DIR)/local-up.log"
	@echo "Logs: $(LOG_DIR)/local-up.log"

local-test:
	@$(ROOT)/runner/bin/superspark local-test 2>&1 | tee "$(LOG_DIR)/local-test.log"
	@echo "Logs: $(LOG_DIR)/local-test.log"

bench:
	@$(ROOT)/runner/bin/superspark bench --profile "$(PROFILE)" --mode "$(MODE)" 2>&1 | tee "$(LOG_DIR)/bench-$(PROFILE)-$(MODE).log"
	@echo "Logs: $(LOG_DIR)/bench-$(PROFILE)-$(MODE).log"

report:
	@$(ROOT)/benchmarks/reporting/report.py 2>&1 | tee "$(LOG_DIR)/report.log"
	@echo "Logs: $(LOG_DIR)/report.log"

package:
	@$(ROOT)/scripts/bootstrap/package.sh --arch "$(ARCH)" 2>&1 | tee "$(LOG_DIR)/package-$(ARCH).log"
	@echo "Logs: $(LOG_DIR)/package-$(ARCH).log"

validate-k8s:
	@test -n "$(CONFIG)" || (echo "CONFIG= is required"; exit 2)
	@$(ROOT)/deploy/kubernetes/validate.sh "$(CONFIG)"

deploy-k8s:
	@test -n "$(CONFIG)" || (echo "CONFIG= is required (refusing unspecified target)"; exit 2)
	@$(ROOT)/deploy/kubernetes/deploy.sh "$(CONFIG)"

package-yarn:
	@test -n "$(CONFIG)" || (echo "CONFIG= is required"; exit 2)
	@$(ROOT)/deploy/yarn/package.sh "$(CONFIG)"

validate-yarn:
	@test -n "$(CONFIG)" || (echo "CONFIG= is required"; exit 2)
	@$(ROOT)/deploy/yarn/validate.sh "$(CONFIG)"

local-down:
	@$(ROOT)/scripts/bootstrap/local_down.sh 2>&1 | tee "$(LOG_DIR)/local-down.log"
	@echo "Logs: $(LOG_DIR)/local-down.log"

test-airflow:
	@$(ROOT)/scripts/bootstrap/test_airflow.sh 2>&1 | tee "$(LOG_DIR)/test-airflow-make.log"
	@echo "Logs: $(LOG_DIR)/test-airflow.log"
