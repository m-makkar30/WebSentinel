# Convenience targets for local development.
# Most stack commands (docker compose, migrations, demo) are added as those
# parts of the system land — see the roadmap in README.md.

.DEFAULT_GOAL := help

.PHONY: help hooks lint fmt

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

hooks: ## Install pre-commit git hooks.
	pre-commit install

lint: ## Run all pre-commit hooks across the repo.
	pre-commit run --all-files

fmt: ## Auto-format the codebase (ruff --fix, black, prettier via hooks).
	pre-commit run ruff --all-files || true
	pre-commit run black --all-files || true
	pre-commit run prettier --all-files || true
