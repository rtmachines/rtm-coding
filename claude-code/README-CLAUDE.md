# rust-review-kit dla Claude Code

Workflow `/rust-pr-review` uruchamia agenta `rust-reviewer`: kontrole Cargo, analizę
poprawności, osobne sprawdzenie wymagań i raport z dowodami. Wersja Claude ma te same
reguły Miri, aliasowania, async i Loom co wersja Codex.

## Instalacja i użycie

```sh
./install.sh --claude /ścieżka/do/repo
./install.sh --claude --axum --grpc --no-ci /ścieżka/do/repo
```

Wymagane: Bash, Git, jq, Python 3 i awk. Do sprawdzania Rust potrzebne są narzędzia
projektu: Cargo, rustfmt, Clippy oraz cargo-deny z `deny.toml`. Nextest jest opcjonalny.
Hooki używają `args` i `onFailure: block`; wymagają Claude Code 2.1.295 lub nowszego.
Nie dodają automatycznych zgód na uruchamianie Cargo ani nie instalują pluginów.

Po instalacji dostosuj `REVIEW.md`, politykę `deny.toml` i features do projektu.
Uruchom Claude Code w repo, zaakceptuj zaufanie dokładnie temu katalogowi i sprawdź
`/agents`, `/skills` oraz `/hooks`, a następnie:

```text
/rust-pr-review origin/main Sprawdź zgodność z wymaganiami opisanymi w REQUIREMENTS.md.
```

Domyślny zakres obejmuje gałąź i lokalne zmiany względem wspólnego przodka
z `origin/main`. Pliki untracked są sprawdzane oddzielnie. Możesz jawnie wybrać
wyłącznie commity PR albo lokalne zmiany względem HEAD. Niepoprawna baza kończy
zbieranie kontekstu błędem; nie jest zastępowana przez HEAD.

## Wiedza i narzędzia

Instalator kopiuje offline `.claude/skills/rust-skills/` z
[rtmachines/rust-skills](https://github.com/rtmachines/rust-skills), przypiętego do
`a1e290d53d43a85421ff16dde23b5f8ec0b48539`. Agent czyta indeks i reguły istotne dla
zmiany, zapisując rewizję i wykorzystane pliki. Licencje i pochodzenie znajdują się
w `.claude/rust-review-kit/`. Podręcznik Apollo stanowi materiał uzupełniający.
Kontrakty projektu, rzeczywista edition, MSRV i wersje zależności mają pierwszeństwo.

Agent ma dostęp do natywnego narzędzia `LSP`. Włączony plugin Rust i dostępny plik
rust-analyzer nie wystarczają do zadeklarowania użycia: musi udać się zapytanie
semantyczne w sprawdzanym projekcie. Raport zawsze zawiera `rust-lsp`, `lsp-used`,
dowody i ograniczenia. Bez działającej integracji agent kontynuuje analizę źródeł
i jawnie zapisuje UNAVAILABLE/NO. Sam brak LSP nie wymusza eskalacji.

Jawna lista narzędzi agenta nie dziedziczy MCP. Aby korzystać z własnego serwera
code-review-graph, rust-lsp albo dokumentacji zależności, dopisz jego dokładne
narzędzia odczytu do `tools` w `.claude/agents/rust-reviewer.md`. Agent sprawdza
rzeczywistą dostępność; nie zakłada, że integracje Codex istnieją w Claude.

Opcjonalny reviewdog prezentuje diagnostykę lokalnie:

```sh
RUST_REVIEWDOG=1 bash .claude/skills/rust-pr-review/scripts/gates.sh
```

Kod wyjścia Clippy decyduje o wyniku bramki. Brak reviewdog, błąd parsera lub pusty
raport po filtrowaniu nie zmieniają FAIL na PASS. Surowe logi pozostają dostępne.
Publikacja komentarzy wymaga osobnego zlecenia.

## Warunki decyzji

- **APPROVE**: wymagane kontrole i spec PASS, bez P0/P1 i otwartych ryzyk bezpieczeństwa.
- **REQUEST_CHANGES**: wykazany błąd blokujący albo niespełnione kontrole/wymagania.
- **ESCALATE**: nierozstrzygnięty obowiązek bezpieczeństwa, wraz z dowodami potrzebnymi
  do jego zamknięcia. Może też zawierać już wykazane błędy.
- **INCOMPLETE**: brak zwykłych wymaganych kontroli albo pełnych wymagań do oceny.

Dla zmienionych granic unsafe/FFI potrzebne są celowane testy **Miri oraz osobna
analiza aliasowania/provenance**. Żywa alokacja nie dowodzi poprawności zachowanego
wskaźnika. Nieznany kontrakt obcej biblioteki i rozbieżność modeli aliasowania
pozostają otwartym ryzykiem nawet przy części zielonych testów.

Zmiany async wymagają stosownych testów **deadlocków, anulowania i zakończenia zadań**.
Własne protokoły synchronizacji wymagają **Loom oraz argumentu o niezmiennikach
i porządkach pamięci**. Model przerwany limitem, timeoutem albo bez istotnych
przeplotów nie stanowi PASS. Kontrakt dostawcy bez wymaganych testów implementacji
nie zamyka eskalacji. Po uzyskaniu kompletnego dowodu review może dać APPROVE;
samo występowanie słów `unsafe` czy `Ordering` nie wymusza ESCALATE.

Testy dotyczą dokładnie ocenianego kodu. Brakujące próby można przygotować w izolowanym
katalogu, gdy wykonanie jest dozwolone, zapisując hashe źródeł, komendy, wersje,
konfigurację i logi. Reviewer nie naprawia badanego kodu. Nie uruchamia podejrzanego
UB natywnie. Miri nie dowodzi poprawności dowolnej natywnej biblioteki FFI.

## Hooki i bramki

| Element | Zachowanie |
|---|---|
| UserPromptSubmit | kieruje prośby o review do skilla; nie uruchamia automatycznie specjalisty |
| PreToolUse agenta | odrzuca oczywiste modyfikacje; resztę poddaje uprawnieniom Claude Code |
| Stop agenta | sprawdza kompletny raport tym samym walidatorem co ręczne wywołanie |
| PreToolUse przed commitem | uruchamia kontrole bez cache i bez przepuszczania po kilku błędach |
| `rust-gates.yml` | uruchamia ten sam skrypt Cargo co lokalne review |

Nie ma globalnego Stop, który wymuszałby naprawę celowo błędnego kodu podczas review.
Poprawny raport ESCALATE/INCOMPLETE może zakończyć pracę. Brak raportu i sprzeczne
APPROVE są odrzucane przy każdej próbie; nie ma licznika „przepuść po N błędach”.
Claude Code ma własne limity kontynuacji hooków, więc lokalny hook nie jest gwarancją
branch protection. Wymagane kontrole na hostingu konfiguruje się osobno.
Samo `claude -p` nie włącza hooków z frontmattera agenta w niezaufanym katalogu.
W automatyzacji przekaż jawnie tę samą definicję przez `--agents`, albo użyj repo
wcześniej zatwierdzonego w interaktywnej sesji. Sprawdź ślad wykonania hooków.

```sh
bash .claude/skills/rust-pr-review/scripts/context.sh origin/main
bash .claude/skills/rust-pr-review/scripts/gates.sh
bash .claude/skills/rust-pr-review/scripts/check-report.sh /tmp/review.md
```

Nextest jest uzupełniany doctestami. Bez nextest używane jest cargo test obejmujące
doctesty. Brak cargo-deny lub konfiguracji daje NOT RUN. `RUST_GATE_FEATURES=''`
wybiera domyślne features; można też przekazać odpowiednie flagi do gates.sh.

Walidator kontroluje strukturę i spójność deklaracji, a nie prawdziwość dowodów.
Hooki nie stanowią izolacji wykonania: Bash, build.rs, makra i testy mogą uruchamiać
kod projektu. Używaj uprawnień i środowiska odpowiednich dla zaufania do źródła.

## Aktualizacja i testy

Zwykła instalacja zachowuje istniejące pliki. `--force` aktualizuje pliki kitu,
zachowując dodatkowe pliki i ustawienia użytkownika. Przed aktualizacją przejrzyj
własne zmiany w dostarczanych plikach, szczególnie REVIEW.md i agencie. Instalator
odrzuca cele prowadzące przez symlinki i niepoprawny settings.json. Usuwa wyłącznie
rozpoznane stare hooki kitu; obce hooki pozostają.

```sh
bash tests/test-claude.sh
python3 tests/test-claude-hooks.py
bash tests/test-claude-install.sh
python3 tests/run-claude-regressions.py /tmp/claude-review-run --phase all
```

Zestaw oddziela automatyczne próby od świeżych raportów modelu. Brak raportów lub
oceny ich dowodów daje INCOMPLETE/FAIL. Stare raporty Codex nie są raportami Claude.
Instrukcja uruchamiania prób: [tests/claude/README.md](tests/claude/README.md).
Ostatnia pełna weryfikacja: [wyniki i paczka dowodów z 2026-10-25](docs/verification/2026-10-25-claude-parity/SUMMARY.md).

Konfigurację natywną oparto na dokumentacji Claude Code:
[skills](https://code.claude.com/docs/en/skills),
[subagents](https://code.claude.com/docs/en/sub-agents),
[hooks](https://code.claude.com/docs/en/hooks).
