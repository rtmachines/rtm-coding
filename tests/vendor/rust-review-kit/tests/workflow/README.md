# Jeden zestaw regresji workflow Rust

Zestaw łączy wcześniejsze eksperymenty w 11 wejść do review i 49 automatycznych
kontroli. Powtórki tego samego źródła są scalone, ale zachowano dodatkowe próby.
`cases.json` jest kluczem oceny — nie przekazuj go reviewerom.

## Uruchomienie

Wymagane: Python 3.12+, Git, Bash, timeout, Rust/Cargo, rustfmt, Clippy, cargo-deny,
nightly z Miri i przygotowanym sysroot oraz zależności z istniejącego Cargo.lock
w lokalnym cache. nextest jest opcjonalny. Zestaw pracuje offline, nie instaluje
narzędzi ani zależności. Stan advisory DB może być nieaktualny; review ma to ujawnić.

Z katalogu kitu, z nowym katalogiem wynikowym:

```sh
python tests/run-workflow-regressions.py /tmp/rust-workflow-regression
```

Polecenie odtwarza wejścia z zamrożonych archiwów, instaluje **bieżący** workflow,
wykonuje oracles i zapisuje SUMMARY.md. Nie nadpisuje istniejącego katalogu. Kod 2
po poprawnych kontrolach oznacza oczekiwanie na świeże review i ocenę ich dowodów,
**nie zaliczenie pełnego workflow**. Nie uruchamia modelu językowego przez niejawne
API, nie wymaga klucza ani nie używa dawnych raportów jako nowych wyników.

Zleć świeżym reviewerom zadania z `review-requests.json`. Udostępnij każdemu wyłącznie
jego repo i katalog wynikowy; nie pokazuj klucza, oracle, innych ocen ani starych
raportów. Użycie kilku reviewerów w partiach jest dopuszczalne, ale opisz tę metodę.
Każdy zapisuje `reviews/ID/report.md`, logi, polecenia/statusy i hashe przed/po.
Review jest względem origin/main, także dla dirty/untracked. Nie naprawia wejścia.

Następnie niezależny oceniający czyta pełne raporty, źródła i dowody. Zapisuje
`semantic-assessment.json`: obiekt z kluczami 01–11; każdy ma `pass` (boolean),
`reason` (uzasadnienie) i `evidence` (niepusta lista ścieżek do sprawdzonych dowodów).
Dla wykrywania błędów sprawdza każdy mechanizm z cases.json, a nie sam werdykt lub
wystąpienie nazwy funkcji. Dla eskalacji i zamknięcia sprawdza zakres dowodu, wykonanie
właściwych testów i brak przypisywania mockowi gwarancji nieznanego dostawcy.

```sh
python tests/run-workflow-regressions.py /tmp/rust-workflow-regression --phase assess
```

Końcowy kod 0 wymaga: ukończonych zielonych diagnostyk, wszystkich świeżych raportów,
poprawnej struktury i werdyktów, niezmienności źródeł/Git oraz pozytywnej oceny
semantycznej. Kod 1 oznacza niezaliczone lub nieukończone diagnostyki/oceny; kod 2
oczekiwanie na raporty/ocenę po poprawnym zakończeniu diagnostyk. Sam walidator formatu
nie dowodzi jakości review. Nie wolno wpisywać pozytywnej oceny bez czytania dowodów.

Dostępne osobne fazy `prepare`, `diagnostics`, `assess` pozwalają uruchomić review
równolegle z oracle. `--phase diagnostics --rerun` zachowuje poprzednią próbę w attempts/
i wykonuje nową; wcześniejsze porażki nie są wymazywane.

## Pokrycie

- Sześć błędów logiki oraz poprawna kontrola, debug/release; także zmiany unstaged
  i plik untracked w review.
- Nieprawidłowe krótkie/niewyrównane odczyty i UAF, wykonywane wyłącznie pod Miri.
- Pełny cykl retained pointer i ruchy Box, oba modele aliasowania; pierwotny węższy
  test odtwarzający różnicę Stacked/Tree Borrows oraz poprawna kontrola.
- Deadlock, anulowanie i zamknięcie kanału zgody, odłączenie zadania zamiast stop,
  destructor completion i uruchomiony spawn_blocking; błędna/poprawna publikacja.
- Brak kontraktu quiescence FFI, niedokończony Loom, nieznane anulowanie dostawcy.
- Ukończony Loom, pełny lokalny dostawca z testami, kontrola z samym kontraktem.
- Mutacja powtarzająca efekt przy retry odrzucana przez testy i Loom.
- Instalator, gates i walidator raportów (tests/test-codex.sh), plus 5 testów samego
  runnera: obcy błąd kompilacji, zero testów, timeout i niewłaściwy kod wyjścia nie
  mogą udawać trafnego kontrprzykładu.

Timeout procesu nie jest dowodem deadlocka. Oczekiwany błąd musi mieć właściwy kod
wyjścia i diagnostykę; zwykłe niepowodzenie kompilacji nie zalicza usterki. Celowe
FAIL na wadliwym kodzie są sukcesem oracle, a ich logi zachowują rzeczywisty wynik.
Model publikacji ma sześć wykonań w przypiętym zestawie zależności; zmiana wersji
Loom może wymagać przeglądu tego oczekiwania, nie automatycznej aktualizacji snapshotu.

Zamrożone archiwa pozostają w tests/e2e/results. Runner zapisuje ich SHA-256 i hashe
wejść, a kopie oracles są poza repozytoriami review. Aktualizuj przypadki i oczekiwania
świadomie. Kopiowane materiały z poprzednich eksperymentów zachowują historyczne wyniki;
nie wolno stosować nowego schematu walidacji do starych raportów i przedstawiać tego
jako nowe review.

Acme to lokalny dostawca testowy: ledger, stałe ID, deduplikacja, quiescent restore.
Nie testuje realnego SDK, crash durability ani zewnętrznego systemu biznesowego.
Miri i skończone modele Loom nie stanowią dowodu wszystkich możliwych zachowań.

Zapis pełnego przebiegu: [2026-10-24](../e2e/results/2026-10-24-regression/RESULTS.md).

Integracja GitHub Actions i dostarczanie raportów: [CI](ci/README.md). Zielone kontrole
automatyczne są osobnym statusem; bramka świeżych review nie zalicza brakujących raportów.
