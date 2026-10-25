# Regresje skilli w CI

Workflow uruchamia się dla każdego PR, push do main oraz ręcznie. Brak filtrów
ścieżek zapewnia obecność obu statusów również przy zmianach dokumentacji.

- `workflow-regressions / automatic`: zgodność opublikowanych skilli Codex, testy
  granicy publikacji i bramki oraz 49 kontroli Rust (w tym Miri i Loom) dla każdego
  wariantu. Dla Claude wykonuje też testy hooków, instalatora, runnera i prób
  akceptacji/odrzucenia paczki.
- `workflow-regressions / fresh-reviews`: wymaga udanej automatyki i kompletu
  11 raportów z dowodami oraz oceną semantyczną dla dokładnej wersji i wejść
  każdego wariantu: Codex i Claude.
  Brak, nieaktualność lub uszkodzenie paczki oznaczają niepowodzenie.

`vendor/rust-review-kit/` zawiera zestaw źródłowy wraz z zamrożonymi wejściami.
Paczka dowodów z 25 października 2026 dla fingerprintu
`be8a1dc3533135a809fa926673ae8aa96771482325e7cff4340e69d5ea42b940`
pozostaje historyczna: dodanie kontroli rust-lsp zmieniło workflow i schemat raportu.
Paczka `07f73acb0514b733a6562cf129c4fec7e7c6b2a4422d3a9d8f91cc32d645f20e`
pozostaje dowodem historycznym po dodaniu LSP. Integracja lokalnej bazy rust-skills
zmieniła fingerprint na `2f9acd927a3c9cdb1fde54c98db0596a611d129cdafcedc90e91c97a45d1f6df`.
Nowa paczka zawiera 11 świeżych review i 468 plików dowodowych. Wynik lokalny:
49/49 kontroli i 11/11 akceptacji; bramka CLI przyjęła paczkę na osobno przygotowanych
identycznych wejściach. Trzej niezależni reviewerzy pracowali w partiach, a osobny
oceniający przeczytał raporty, źródła i dowody. Wszystkie raporty zapisują faktyczne
użycie LSP oraz wybrane reguły rust-skills z przypiętego commita. Nie przepisano
historycznych raportów pod nowy hash. Szczegóły: [wyniki](RUST-SKILLS-REGRESSION.md).
Testy kontraktu raportu symulują niedostępność API, błędy
ładowania i timeout; nie są wykonaniem review przez model ani awarią żywego serwera.
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

## Claude Code

`../claude-code/` zawiera niezmieniony zestaw zweryfikowany przez natywny Claude Code
2.1.308. Fingerprint: `accbf87cfed35bfbb1c90b2d2855bf65c8bd9748506b490e67b3d164081c2a3c`.
Raporty, transkrypty i oceny semantyczne są w
[paczce weryfikacyjnej](../claude-code/docs/verification/2026-10-25-claude-parity/SUMMARY.md).
Nie przepisano raportów Codex na Claude ani nie zmieniono ich przypisania do wersji.

CI przygotowuje osobny aktualny przebieg Claude i wykonuje jego 49 kontroli.
`check_claude_evidence.py` wymaga zgodności aktualnej wersji, świeżych wejść, raportów,
natywnych transkryptów oraz niezależnych ocen. Czyta archiwum jako dane i korzysta
z walidatora z checkoutu, nie uruchamia skryptów ani konfiguracji Git z dowodów.
Testy mutacyjne sprawdzają przyjęcie prawdziwej paczki i odrzucanie brakujących,
zmienionych lub nieaktualnych materiałów.

Przykład lokalnego sprawdzenia:

```sh
python claude-code/tests/run-claude-regressions.py /tmp/claude-ci-run --phase prepare
python claude-code/tests/run-claude-regressions.py /tmp/claude-ci-run --phase diagnostics
CLAUDE_EVIDENCE_RUN=/tmp/claude-ci-run python tests/test_claude_evidence.py
python tests/check_claude_evidence.py /tmp/claude-ci-run
```

Zmiana fingerprintu wymaga nowych rzeczywistych review zgodnie z
[instrukcją runnera Claude](../claude-code/tests/claude/README.md), nowej oceny dowodów
i paczki. Samo przeliczenie manifestu wcześniejszych raportów nie jest nowym review.
Automatyczne CI nie wywołuje modeli. Test natywnego transportu hooków wymaga
osobnego świadomego uruchomienia `CLAUDE_NATIVE_TESTS=1`.
