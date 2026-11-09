.PHONY: help tui dry-run clean clean-auto list scan simslim-on simslim-off remove-ai status

help:
	@echo "Mac Developer Cleaner & Optimizer"
	@echo "================================="
	@echo "make tui         - Avvia la Terminal UI interattiva (default)"
	@echo "make dry-run     - Simula la pulizia completa senza cancellare file"
	@echo "make clean       - Avvia la pulizia chiedendo conferma"
	@echo "make clean-auto  - Esegue la pulizia automatica completa (-y)"
	@echo "make list        - Elenca tutti i moduli di pulizia disponibili"
	@echo "make simslim-on  - Ottimizza il Simulatore iOS riducendo la RAM"
	@echo "make simslim-off - Ripristina i demoni del Simulatore iOS"
	@echo "make remove-ai   - Disattiva Apple Intelligence locale via removemacai"

tui:
	./clean_mac.py --tui

dry-run:
	./clean_mac.py --dry-run

clean:
	./clean_mac.py --cli

clean-auto:
	./clean_mac.py --yes

list:
	./clean_mac.py --list

simslim-on:
	@which simslim >/dev/null 2>&1 && simslim on || echo "simslim non installato (esegui: brew install mobai-app/tap/simslim)"

simslim-off:
	@which simslim >/dev/null 2>&1 && simslim off || echo "simslim non installato"

remove-ai:
	@which removemacai >/dev/null 2>&1 && removemacai off || echo "removemacai non installato (esegui: brew install omlahore/tap/removemacai)"
