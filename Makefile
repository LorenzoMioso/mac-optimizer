.PHONY: help tui dry-run clean clean-auto list test sync simslim-on simslim-off remove-ai

help:
	@echo "Mac Developer Cleaner & Optimizer"
	@echo "================================="
	@echo "make tui         - Avvia la Terminal UI interattiva Textual (default)"
	@echo "make test        - Esegue la suite completa di test con pytest via uv"
	@echo "make sync        - Sincronizza l'ambiente virtuale e le dipendenze con uv"
	@echo "make dry-run     - Simula la pulizia completa senza cancellare file"
	@echo "make clean       - Avvia la pulizia chiedendo conferma"
	@echo "make clean-auto  - Esegue la pulizia automatica completa (-y)"
	@echo "make list        - Elenca tutti i moduli di pulizia disponibili"
	@echo "make simslim-on  - Ottimizza il Simulatore iOS riducendo la RAM"
	@echo "make simslim-off - Ripristina i demoni del Simulatore iOS"
	@echo "make remove-ai   - Disattiva Apple Intelligence locale via removemacai"

sync:
	uv sync

test:
	uv run pytest -v

tui:
	uv run mac-optimizer --tui

dry-run:
	uv run mac-optimizer --dry-run

clean:
	uv run mac-optimizer --cli

clean-auto:
	uv run mac-optimizer --yes

list:
	uv run mac-optimizer --list

simslim-on:
	@which simslim >/dev/null 2>&1 && simslim on || echo "simslim non installato (esegui: brew install mobai-app/tap/simslim)"

simslim-off:
	@which simslim >/dev/null 2>&1 && simslim off || echo "simslim non installato"

remove-ai:
	@which removemacai >/dev/null 2>&1 && removemacai off || echo "removemacai non installato (esegui: brew install omlahore/tap/removemacai)"
