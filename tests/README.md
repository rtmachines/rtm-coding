# Regresje skilli w CI

Workflow uruchamia się dla każdego PR, push do main oraz ręcznie. Brak filtrów
ścieżek zapewnia obecność obu statusów również przy zmianach dokumentacji.

- `workflow-regressions / automatic`: zgodność opublikowanych skilli, 6 testów
  granicy publikacji, 19 testów bramki oraz 49 kontroli Rust (w tym Miri i Loom).
- `workflow-regressions / fresh-reviews`: wymaga udanej automatyki i kompletu
  11 raportów z dowodami oraz oceną semantyczną dla dokładnej wersji i wejść.
  Brak, nieaktualność lub uszkodzenie paczki oznaczają niepowodzenie.

`vendor/rust-review-kit/` zawiera niezmieniony zestaw źródłowy wraz z zamrożonymi
wejściami i paczką dowodów z 25 października 2026. Zachowano fingerprint
`be8a1dc3533135a809fa926673ae8aa96771482325e7cff4340e69d5ea42b940`.
To ponowne użycie raportów dla identycznych skilli i wejść, nie nowe wykonanie LLM.
CI ponownie wykonuje automatykę; dowodów z paczki nie wykonuje jako kodu.
Opcjonalne skille wewnątrz zestawu są danymi dla testów instalatora.

Kontrola `check_skill_binding.py` porównuje pełny zestaw plików publicznego `skills/`
z testowaną kopią. Wyłącza wyłącznie README publikacji i trzy jawnie wymienione
pliki licencji/atrybucji. Nowy, zmieniony, usunięty plik lub symlink blokuje CI.

## Aktualizacja

1. Zmień publiczny skill i jego odpowiednik w
   `tests/vendor/rust-review-kit/codex-template/.agents/skills/`.
2. Z katalogu `tests/vendor/rust-review-kit` przygotuj nowy przebieg:
   `python tests/run-workflow-regressions.py /tmp/new-review-run`.
3. Dostarcz autentyczne review według `review-requests.json`, dowody wykonania
   i niezależną ocenę semantyczną. Nie przepisuj dawnych raportów pod nowy hash.
4. Uruchom `python tests/workflow/ci/manage.py export /tmp/new-review-run`
   i dodaj wyeksportowany katalog do PR.

Zmiany testowanego workflow, testów, narzędzi lub archiwów również zmieniają
fingerprint i wymagają nowej paczki. Sam adapter GitHub Actions w korzeniu repo
i kontrola publikacji są weryfikowane w normalnym review PR; nie są objęte
historyczną oceną skilli. Szczegóły procesu: [instrukcja zestawu](vendor/rust-review-kit/tests/workflow/ci/README.md).

Sam YAML nie ustanawia ochrony gałęzi. Oba powyższe statusy należy ustawić jako
wymagane w regułach `main`. Paczka potwierdza zgodność wersji i kompletność,
nie tożsamość autora: treść nowych dowodów wymaga normalnego review PR.
