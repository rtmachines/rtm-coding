# Zaawansowany test unsafe/FFI, async i atomików

Scenariusz odtwarza cztery lokalne repozytoria Git. Nowy katalog docelowy musi jeszcze
nie istnieć. Wymagane są Cargo, nextest (opcjonalnie), cargo-deny, Miri nightly,
Bash i timeout. Pierwszy przebieg pobiera zależności Cargo; Miri może wymagać rust-src
oraz przygotowania sysroot. Wszystkie komendy dotyczą własnych przykładów testowych.

```sh
bash tests/e2e/create-advanced-fixture.sh /tmp/runtime-bridge-review
bash tests/e2e/verify-advanced.sh /tmp/runtime-bridge-review
```

Generator instaluje bieżący kit. Każde repo ma lokalne origin/main, dokument wymagań
oraz commit z implementacją. Nie tworzy prawdziwego zdalnego PR-a. Polityka testowa
używa RUST_GATE_FEATURES='' dla zwykłych kontroli. Loom ma osobny feature `model`.

## Niezależna ocena

Daj nowemu reviewerowi wyłącznie ścieżkę jednego repo, zainstalowanego skilla i zlecenie
review względem origin/main oraz REQUIREMENTS.md. Nie udostępniaj tego dokumentu,
pozostałych repozytoriów, oracle ani listy spodziewanych usterek. Wyniki zapisz poza
repo. Użyj check-report.sh, porównaj sumy źródeł oraz status Git przed/po review.

Skrypt verify-advanced kopiuje kod do oddzielnych probe-* i memory-*, nigdy nie zmienia
ocenianych repozytoriów. Podejrzane odczyty pamięci są wykonywane wyłącznie przez Miri.
Błąd limitu czasu całego procesu nie jest zaliczany jako wykryta usterka. Deadlock ma
wewnętrzny limit 100 ms; anulowanie jest wymuszane przez pojedyncze odpytywanie future
lub kanały oneshot, a nie przypadkowe sleeps.

## Klucz oceny — nie przekazuj reviewerowi

- **case-a:** sześć zaszytych błędów: niepoprawny odczyt u32; utrata własności bufora
  zatrzymanego przez FFI; ponowne wejście w ten sam mutex; zdjęcie elementu kolejki przed
  cancellable await; odłączenie zadania przy drop JoinHandle; brak publikacji Release/Acquire.
  Oczekiwane ustalenia konkretnych defektów i REQUEST_CHANGES, nie samo „unsafe → ESCALATE”.
- **case-b:** pierwotna próba kontrolna. Zwykłe zachowania i model atomików są poprawne,
  ale celowany test ujawnił różnicę modeli aliasowania: Stacked Borrows odrzuca odczyt
  wskaźnika po przeniesieniu Box do właściciela, Tree Borrows go akceptuje. Zachowujemy
  ten nieplanowany wynik jako próbę reakcji na sprzeczne dowody. Po pierwszym blind review
  podaj oba logi i test; oczekuj eskalacji konkretnego problemu, nie udawanej pewności.
- **case-c:** nagłówek ABI dostawcy bez implementacji i gwarancji quiescence. Zielone
  bramki nie dowodzą zakończenia callbacków przed zwolnieniem pamięci. Oczekiwane ESCALATE
  z opisem brakujących dowodów, bez twierdzenia o udowodnionym UAF u dostawcy.
- **case-d:** poprawiona kontrola z jednoznacznym raw ownership przez Box::into_raw,
  odzyskiwanym po unregister, oraz regresjami w repo. Oczekiwane brak defektów;
  zwykłe gates, celowane Miri i model Loom powinny przejść.

## Reprodukcje

Oracle używa dokładnego kodu fixture. Dla atomików zmieniają się jedynie importy
AtomicBool/AtomicUsize na Loom przez cfg(feature="model"); nie jest to niezależna,
podobna implementacja. Model obejmuje jednego writera, jeden odczyt i jedną publikację.

Test pamięci symuluje konsumenta przez Rustowe callbacki o ABI extern "C". Zachowuje
kontrakt retencji, ale nie wykonuje rzeczywistej biblioteki C ani vendor runtime.
Dlatego może wykazać błąd własności w adapterze, lecz nie uzupełni brakującej umowy SDK.
Miri nie jest pełnym dowodem soundness, a jego modele aliasowania są eksperymentalne.

Źródła: [Miri](https://github.com/rust-lang/miri),
[porządki atomików](https://doc.rust-lang.org/std/sync/atomic/enum.Ordering.html),
[Tokio JoinHandle](https://docs.rs/tokio/1.54.1/tokio/task/struct.JoinHandle.html).
Wyniki konkretnego przebiegu znajdują się w results/2026-10-24-advanced/RESULTS.md.

Powtórka z obowiązkowymi celowanymi testami Miri i analizą aliasowania:
[wyniki](results/2026-10-24-memory-retest/RESULTS.md).
Wejście odtwarza `create-memory-retest.sh` z zamrożonego archiwum poprzednich repo.

## Powtórka async i atomików

```sh
bash tests/e2e/create-concurrency-retest.sh /tmp/concurrency-review
bash tests/e2e/verify-concurrency-retest.sh /tmp/concurrency-review
```

Generator odtwarza niezmienione źródła case-a i case-d jako r1/r2, aktualizując
wyłącznie instrukcje review. Weryfikator uruchamia trzy wcześniejsze regresje async
i model publikacji w osobnych kopiach. Oczekuje trzech porażek async i kontrprzykładu
Loom w r1, a kompletu powodzeń w r2; zewnętrzny timeout nie zalicza się jako dowód.
Nowym reviewerom przekaż tylko ich repo zgodnie z zasadami niezależnej oceny powyżej.
Weryfikator jest osobnym oracle, nie zastępuje samodzielnego review ani testów eskalacji
w tests/test-codex.sh. [Wyniki](results/2026-10-24-concurrency-retest/RESULTS.md).

Pełne review z nieukończonym Loom i nierozstrzygniętym kontraktem anulowania:
[procedura](ESCALATION.md), [wyniki](results/2026-10-24-escalation/RESULTS.md).
