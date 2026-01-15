install: ## Install dependencies using uv
	uv sync

test: ## Run tests
	uv run pytest tests/ -v

format: ## Run ruff formatter and linter
	uv run ruff check --fix .
	uv run ruff format .

update_reqs: ## Update requirements.txt
	pipreqs --force .