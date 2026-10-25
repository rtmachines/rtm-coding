# Analiza i adaptacja do Codex

## Wniosek

Warto zachować zestaw wiedzy Rust, oddzielny spec pass, ocenę ryzyk i kontrolę pochodzenia.
Warstwę wykonawczą Claude należy zastąpić natywnymi skillami Codex i jawnymi skryptami.
Samo przemianowanie `.claude` na `.codex` nie przenosi hooków, uprawnień ani subagentów.

## Najważniejsze ustalenia

| Oryginał | Problem | Adaptacja |
|---|---|---|
| `context: fork`, `agent`, `allowed-tools`, `$ARGUMENTS`, blok dynamicznego Bash | zależność od mechaniki Claude | zwykły SKILL.md i jawne uruchomienie context.sh |
| CLAUDE.md z `@REVIEW.md` | brak natywnego bloku instrukcji Codex | AGENTS.md z poleceniem odczytu REVIEW.md |
| Stop/PreToolUse/SubagentStop | brak przeniesionej implementacji tych hooków | jawne skrypty i CI; brak deklaracji twardej blokady lokalnej |
| allowlista Bash i brak Edit/Write | nie izoluje skutków build.rs/testów | uczciwy opis uprawnień i wykonania kodu |
| fallback merge-base → HEAD | błędna baza mogła ukryć zmiany gałęzi | błąd wymagający poprawnej bazy |
| nextest bez doctestów lokalnie | zakres testów węższy niż CI | dodatkowy cargo test --doc |
| cache wyniku zależny od ograniczonego diffu | nie obejmował całej konfiguracji i wszystkich wejść | brak cache wyników; cargo zachowuje zwykły cache kompilacji |
| pomijanie cargo-deny bez konfiguracji | brak kontroli mógł wyglądać na sukces | jawne NOT RUN i niezerowy kod |
| walidator akceptował APPROVE + NOT RUN | zatwierdzenie bez dowodów | INCOMPLETE; kontrola kompletności i sekcji Residual risks |
| severity przypisana automatycznie do panik/testów | możliwe zawyżone lub fałszywe uwagi | ocena skutków, osiągalności i regresji |
| publiczne API automatycznie kierowane do GraphQL | publiczne gRPC odrzucane przez własny skill | wybór na podstawie rzeczywistego protokołu |
| twarde reguły Apollo i smells | heurystyki mogły uchodzić za dowód błędu | pierwszeństwo kontraktów i dowodów; jawne zastrzeżenia |

## Projekt docelowy

Źródłem ogólnej wiedzy Rust jest [rtmachines/rust-skills](https://github.com/rtmachines/rust-skills).
Reviewer czyta indeks i reguły istotne dla diffu z dołączonej lokalnej kopii tego forka.
Instalator działa bez sieci; commit kolekcji jest przypięty w `vendored.tsv`.
Dołączony podręcznik Apollo pozostaje materiałem uzupełniającym. Reguły nie zastępują
kontraktów projektu ani weryfikacji ustaleń w źródłach i testach.

Codex używa `.agents/skills` i instrukcji `AGENTS.md`. Opcjonalne skille zachowują
wywoływanie tylko na żądanie przez `agents/openai.yaml`. Główny skill działa w bieżącej
sesji, bez zależności od automatycznej delegacji. Graf zawęża analizę, LSP pomaga w
semantyce Rust, a źródło i testy pozostają podstawą ustaleń. Te integracje są opcjonalne.

Instalator zachowuje istniejące pliki, obsługuje ścieżki ze spacjami, odrzuca dowiązania
w ścieżkach docelowych i nie modyfikuje globalnych ustawień. Oryginał został zachowany
w `template/`, `optional/`, `install-claude.sh` oraz dokumentacji `*-CLAUDE.md`.

## Granice weryfikacji

Testy w `tests/test-codex.sh` sprawdzają instalację i ponowne uruchomienie, zachowanie
istniejących instrukcji, błędną bazę Git, zmiany lokalne/untracked, statusy gates,
doctesty, brak cargo-deny i walidację raportu. Cargo jest zastępowane kontrolowanym
programem testowym, aby testować decyzje skryptu bez pobierania zależności.
To nie jest end-to-end review prawdziwego PR-a ani dowód jakości ocen modelu.
Folder zestawu nie jest repozytorium Git i nie zawiera aplikacji Rust do kompilacji.

## Źródła

- [Skills Codex — lokalne .agents/skills](https://learn.chatgpt.com/docs/build-skills)
- [AGENTS.md — instrukcje i reguły review](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- Przypięte materiały Rust: `vendored.tsv` i `licenses/`.

## Zmiana po eksperymentach unsafe/FFI

Pierwszy przegląd nie znalazł problemu aliasowania związanego z ruchem właściciela Box;
ogólne Miri wykonywało tylko testy serwisu. Workflow wymaga teraz celowanego wykonania
zmienionych granic pamięci i niezależnego uzasadnienia aliasowania. Pozwala tworzyć
izolowane próby na niezmienionej implementacji, bez naprawiania ocenianego repo.
Brak dowodów bezpieczeństwa oraz sprzeczne modele blokują APPROVE przez ESCALATE.
Nowa sekcja raportu i testy walidatora sprawdzają tę spójność. Same instrukcje ani
walidator formatu nie są technicznym dowodem soundness.

## Zmiana po eksperymentach async i atomików

Workflow wymaga teraz kontrolowanych prób deadlocków, anulowania i zakończenia zadań
oraz modeli Loom dla zmienianych własnych protokołów synchronizacji. Model musi
wykonywać ocenianą implementację ze śledzonymi prymitywami, sprawdzać kontrakt i
ujawniać limity eksploracji. Osobna analiza porządków pamięci pozostaje obowiązkowa.
Niepełna eksploracja lub brak odpowiednich prób wymaga ESCALATE, a potwierdzony
kontrprzykład blokuje APPROVE. Walidator sprawdza deklaracje, nie prawdziwość dowodów.
Wyniki ponownego review: [raport](tests/e2e/results/2026-10-24-concurrency-retest/RESULTS.md).
