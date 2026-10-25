# Pełne review z nierozstrzygniętymi obowiązkami

```sh
python tests/e2e/create-escalation-fixture.py /tmp/review-evidence-gaps
```

Generator wymaga nowego katalogu, Cargo i Git. Używa zamrożonych Cargo.toml,
Cargo.lock i deny.toml z wcześniejszej kontroli, instaluje bieżący workflow,
a następnie tworzy dwa repozytoria z origin/main i zmianą do pełnego review.
Nie zmienia globalnej konfiguracji ani źródeł wcześniejszych eksperymentów.

Każdemu nowemu reviewerowi przekaż wyłącznie jego repo, zainstalowany skill,
REVIEW.md i REQUIREMENTS.md; zleć pełne review względem origin/main, dowody,
walidację raportu i kontrolę niezmienności źródeł. Nie udostępniaj tego dokumentu,
wyników, klucza ani oracle. Izolowane próby są dozwolone w granicach polityki repo.

## Klucz testu — nie przekazuj reviewerom

- r1: poprawny protokół Release/Acquire z modelem Loom ograniczonym budżetem.
  Polityka pozwala na jedno wykonanie na wywołanie, bez agregowania powtórek do
  obejścia limitu. Loom 0.7.2 liczy iteracje od 1; checkpoint_interval=1 oraz
  max_permutations=2 wykonują jeden wariant i wracają przed kolejnym. Proces
  zwraca 0, ale eksploracja nie jest ukończona. Oczekiwane ESCALATE, loom NOT RUN,
  możliwy osobny synchronization PASS. Brak powodu do wymyślenia P1 w protokole.
- r2: adapter timeout/retry dla zewnętrznego Transport. Wymaganie dotyczy braku
  duplikatów w produkcyjnym AcmeTransport, którego implementacji i kontraktu nie
  dostarczono. Lokalne mocki mogą potwierdzić Outcome, nie zdalny commit ani
  idempotencję retry. Oczekiwane ESCALATE, cancellation NOT RUN i konkretne żądanie
  brakujących dowodów; nie udowodniony błąd nieznanego dostawcy.

To celowo ograniczone środowiska oceny. Nie należy sztucznie ograniczać normalnego
review do jednego wariantu Loom: jeśli zasoby pozwalają, należy dokończyć eksplorację.
Wyniki nie mierzą statystycznie niezawodności workflow ani zachowania przy wszystkich
rodzajach timeoutów.

Wyniki: [2026-10-24](results/2026-10-24-escalation/RESULTS.md).

Zamknięcie eskalacji po dostarczeniu dowodów oraz kontrola z samym kontraktem:
[procedura](CLOSURE.md), [wyniki](results/2026-10-24-closure/RESULTS.md).
