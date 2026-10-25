# rust-review-kit — Codex

Zestaw do review PR-ów i zmian Rust: bramki Cargo, analiza poprawności i bezpieczeństwa,
porównanie z wymaganiami oraz raport P0–P3. Domyślny instalator jest dostosowany do Codex.
Wersja Claude Code ma te same wymagania dowodowe; jest dostępna przez `--claude`
i opisana w [README-CLAUDE.md](README-CLAUDE.md).

## Instalacja

```sh
./install.sh /ścieżka/do/repo
./install.sh --axum --grpc /ścieżka/do/repo
./install.sh --all-optional --no-ci /ścieżka/do/repo
```

Wymagania: Bash, Git, awk i narzędzia systemowe. Kontrole: Cargo, rustfmt, clippy,
cargo-deny i projektowy `deny.toml`; nextest opcjonalny (fallback do cargo test).
Instalator nie pobiera narzędzi ani pluginów, nie zmienia konfiguracji globalnej i nie
uruchamia kodu docelowego projektu. Ścieżki ze spacjami należy ująć w cudzysłowy.

Po instalacji dostosuj `REVIEW.md`, `deny.toml` oraz macierz features/toolchain w CI.
Otwórz repo w Codex i wpisz:

```text
$rust-pr-review origin/main Sprawdź zgodność z wymaganiami z opisu PR.
```

Domyślny zakres: wspólny przodek z `origin/main` → bieżące pliki, wraz z lokalnymi
zmianami. Pliki untracked są wykazywane oddzielnie i wymagają osobnego odczytu.
W poleceniu możesz wybrać wyłącznie commity PR lub wyłącznie lokalne zmiany.
Brak wskazanej bazy przerywa zbieranie kontekstu; nie zmienia zakresu na HEAD.

## Instalowane elementy

| Ścieżka | Rola |
|---|---|
| `AGENTS.md` | dopisany jednorazowo blok instrukcji review |
| `.agents/skills/rust-pr-review/` | workflow, referencje i skrypty |
| `.agents/skills/rust-skills/` | lokalna baza wiedzy rtmachines z przypiętego commita |
| `.agents/skills/rust-best-practices/` | uzupełniający podręcznik Apollo |
| `.agents/skills/tailrocks-*-review/` | opcjonalne przeglądy Axum/gRPC/GraphQL |
| `.agents/skills/rust-lib-guidelines/` | opcjonalne wytyczne bibliotek Microsoft |
| `REVIEW.md` | priorytety i polityka projektu |
| `.github/workflows/rust-gates.yml` | kontrole CI, chyba że `--no-ci` |
| `.agents/rust-review-kit/` | licencje, pochodzenie i skrypt kontroli upstream |

Podstawowe źródło ogólnej wiedzy Rust dla `rust-pr-review` to
[rtmachines/rust-skills](https://github.com/rtmachines/rust-skills): indeks `SKILL.md`
i dobrane do zmian pliki `rules/`. Instalator kopiuje do repo dołączoną kolekcję
z commita `a1e290d53d43a85421ff16dde23b5f8ec0b48539`, bez pobierania plików z sieci.
Reviewer czyta ją lokalnie i zapisuje rewizję oraz wykorzystane reguły w raporcie.
Przypięcie i zakres kopii opisuje `vendored.tsv`; licencja MIT jest dołączona.
Baza wiedzy działa offline; bramki Cargo nadal wymagają dostępnych narzędzi i zależności.
Zasady projektu, edition, MSRV i kontrakty mają pierwszeństwo przed ogólnymi wskazówkami.

Zwykła ponowna instalacja zachowuje istniejące pliki i uzupełnia brakujące.
`--force` nadpisuje tylko pliki dostarczane przez kit, bez usuwania dodatkowych plików.
Istniejący blok w `AGENTS.md` trzeba aktualizować ręcznie, również z `--force`.
Aktualizacja bez `--force` zachowuje także stare SKILL.md i walidator; aby wdrożyć nowe
wymagania pamięci, trzeba świadomie zaktualizować skill i politykę REVIEW.md, zachowując
własne reguły projektu. `--force` nadpisuje dostarczane pliki, w tym REVIEW.md.
Jeżeli istnieje `AGENTS.override.md`, trzeba w nim uwzględnić instrukcje kitu.
Domyślna instalacja nie usuwa istniejącej konfiguracji Claude.

## Kontrole i raport

Uruchamiaj z katalogu głównego workspace Cargo:

```sh
bash .agents/skills/rust-pr-review/scripts/context.sh origin/main
bash .agents/skills/rust-pr-review/scripts/gates.sh
bash .agents/skills/rust-pr-review/scripts/gates.sh --no-default-features --features server,tls
bash .agents/skills/rust-pr-review/scripts/check-report.sh /tmp/review.md
```

Gates wypisuje statusy na stdout, komendy i diagnostykę na stderr. Zwraca kod niezerowy
przy błędzie lub niewykonanej wymaganej kontroli. Nextest jest uzupełniany doctestami.
Bez nextest używane jest cargo test, które obejmuje doctesty. Cargo-deny jest sprawdzane
przy każdym przebiegu; brak narzędzia lub konfiguracji daje NOT RUN.
`RUST_GATE_FEATURES=''` wybiera domyślne features zamiast `--all-features`.

Werdykty: `APPROVE`, `REQUEST_CHANGES`, `ESCALATE`, `INCOMPLETE`.
APPROVE wymaga wykonanych wymaganych kontroli, spec PASS i braku P0/P1 oraz nierozstrzygniętych
ryzyk bezpieczeństwa. Dla zmienionych granic unsafe/FFI wymagane są **celowane testy Miri
oraz osobna analiza aliasowania/provenance**. Zielony przebieg niepowiązanych testów nie
spełnia tego wymagania. Gdy brakuje testów, reviewer tworzy izolowaną próbę na dokładnej
kopii źródła, o ile wykonanie jest dozwolone. Nie modyfikuje ocenianego repozytorium.

Każdy nowy raport zawiera `## Memory safety`: zakres REQUIRED/NONE, status Miri,
status aliasowania oraz dowody (testy, polecenia, wersje, flagi, logi i niezmienność kodu).
Nieznany kontrakt FFI, brak możliwości przeprowadzenia celowanej próby albo rozbieżność
modeli aliasowania wymaga ESCALATE. Walidator odrzuca APPROVE przy brakujących dowodach
zadeklarowanych w tych polach, ale nie potrafi sprawdzić prawdziwości testów ani ustalić
samodzielnie, czy autor raportu poprawnie zaklasyfikował zakres.

Zmiany async wymagają celowanych testów deadlocków, anulowania i zakończenia zadań
w odpowiednim zakresie. Własne protokoły synchronizacji wymagają modeli Loom
na śledzonych prymitywach oraz osobnego uzasadnienia niezmienników i porządków pamięci.
Sekcja `## Concurrency` zapisuje zakres, wyniki i dowody obu rodzajów walidacji.
Brak wymaganej próby, niedokończony model lub nierozstrzygnięty niezmiennik wymaga
ESCALATE. N/A wymaga uzasadnienia; sam timeout nie dowodzi deadlocka.
Szczegóły: [weryfikacja współbieżności](codex-template/.agents/skills/rust-pr-review/references/CONCURRENCY-VALIDATION.md).

Starsze raporty bez sekcji Memory safety lub Concurrency nie przechodzą nowego walidatora. Zachowane
raporty eksperymentów dokumentują poprzednie wersje workflow i nie są przepisywane.
Gdy środowisko narzuca własny format review, skill respektuje ten format.

## Co jest egzekwowane

- `AGENTS.md` i skill opisują zachowanie; nie są techniczną blokadą zapisu lub commita.
- Skrypty wykonują sprawdzenia jawnie; kit nie instaluje hooków Stop/PreToolUse Claude.
- CI używa tego samego skryptu co lokalne review. Wymagany status w ochronie gałęzi
  trzeba skonfigurować w repozytorium hostingowym; instalator tego nie robi.
- Cargo i testy wykonują kod projektu. Używaj uprawnień i izolacji odpowiednich do
  zaufania do projektu; deklaracja „review only” nie izoluje build.rs ani testów.
- code-review-graph, Rust LSP i dokumentacja zależności są wykorzystywane, gdy dostępne.
  Brak integracji jest raportowany; nie blokuje całej analizy źródeł.
- Eskalacja wskazuje konkretne nierozstrzygnięte ryzyka, bez fikcyjnego wywołania
  nieobecnych pluginów Trail of Bits. Publikowanie uwag wymaga zlecenia użytkownika.

## Utrzymanie i weryfikacja

```sh
bash tests/test-codex.sh
bash .agents/rust-review-kit/scripts/check-upstream.sh
```

Źródła i lokalne adaptacje: `vendored.tsv`, `THIRD_PARTY_NOTICES.md`.
Wersja Claude: `./install.sh --claude [opcje] /ścieżka/do/repo`.
Analiza migracji: [RECOMMENDATION.md](RECOMMENDATION.md).
Wymagania pamięci: [MEMORY-VALIDATION.md](codex-template/.agents/skills/rust-pr-review/references/MEMORY-VALIDATION.md).

Struktura Codex oparta na oficjalnej dokumentacji:
[skills](https://learn.chatgpt.com/docs/build-skills) i
[AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Zbiorczy zestaw regresji (wykrywanie, eskalacja, zamknięcie): [instrukcja](tests/workflow/README.md).
Konfiguracja CI zestawu i osobna bramka świeżych review: [instrukcja](tests/workflow/ci/README.md).
