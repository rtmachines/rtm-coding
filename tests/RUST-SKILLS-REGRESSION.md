# Regresje po integracji rust-skills — 2026-10-25

Źródło wiedzy: `rtmachines/rust-skills`, commit
`a1e290d53d43a85421ff16dde23b5f8ec0b48539`, 265 reguł dostępnych offline.
Opublikowane 291 plików źródłowych skilli zgadza się z testowanym zestawem.
Wersja workflow: `2f9acd927a3c9cdb1fde54c98db0596a611d129cdafcedc90e91c97a45d1f6df`.
Wiązanie wejść: `8dde84870b5d6bf89e4fea73c389e8377a988d5525d7274ba85ec54468de9e6e`.

## Wyniki lokalne

- 49/49 automatycznych kontroli Rust, Miri, Loom oraz instalatora/gates/walidatora.
- 19/19 testów bramki CI, w tym akceptacja zgodnej paczki i odrzucanie mutacji
  workflow lub wejść; 6/6 testów zgodności publikacji.
- Walidacja skill-creator: rust-pr-review i rust-skills poprawne.
- 11/11 świeżych raportów przyjętych po ocenie semantycznej i kontroli niezmienności.
- 12 mechanizmów błędów wykrytych: sześć logicznych, sześć pamięci/współbieżności.
- Werdykty: 2 REQUEST_CHANGES, 5 ESCALATE, 4 APPROVE.
- Każdy raport dokumentuje rzeczywiste zapytania LSP, reguły wiedzy i ich wersję.

Trzej nowi reviewerzy pracowali niezależnie od poprzednich wyników: partie
01/04/07/10, 02/03/08/11, 05/06/09. Nie otrzymali klucza oczekiwań, oracle ani
starych raportów. Raporty, właściwy kod i surowe dowody ocenił osobno agent nadrzędny.
To 11 review w trzech sesjach, nie 11 statystycznie niezależnych reviewerów.

Pełna tabela wyników:

| Przypadek | Werdykt |
|---|---|
| 01 — błędy logiki, dirty/untracked | REQUEST_CHANGES |
| 02 — poprawna logika | APPROVE |
| 03 — unsafe/FFI, deadlock, anulowanie, worker, atomiki | REQUEST_CHANGES |
| 04 — aliasowanie retained pointer po ruchu Box | ESCALATE |
| 05 — brak kontraktu quiescence FFI | ESCALATE |
| 06 — poprawna pamięć i współbieżność | APPROVE |
| 07 — niepełna eksploracja Loom | ESCALATE |
| 08 — nieznana semantyka dostawcy | ESCALATE |
| 09 — ukończony model, sześć wykonań | APPROVE |
| 10 — pełny lokalny dostawca, kontrakt, testy i model | APPROVE |
| 11 — kontrakt bez implementacji dostawcy | ESCALATE |

## Paczka i bramka

[Paczka](vendor/rust-review-kit/tests/workflow/review-evidence/2f9acd927a3c9cdb1fde54c98db0596a611d129cdafcedc90e91c97a45d1f6df/)
zawiera 468 plików dowodowych z SHA-256 oraz manifest. Wszystkie sumy sprawdzono.
Osobne przygotowanie odtworzyło identyczne suite-identity.json i inputs.json.
Do tych wejść przeniesiono rzeczywiste ukończone diagnostyki, jak między jobami CI;
nie wykonano drugiej lokalnej serii 49 kontroli.

- Bez paczki: kod 2, brak raportów nie daje PASS.
- Poprzednia paczka LSP: kod 1, niezgodne workflow/wejścia.
- Bieżąca paczka, domyślne wyszukiwanie `manage.py gate`: kod 0, 11/11 i 49/49.

CI ponownie wykonuje automatykę na GitHubie. Nie uruchamia LLM ani kodu z dowodów;
sprawdza paczkę i zapisaną ocenę. Wynik zdalny jest osobno widoczny w kontrolach PR.

## Zakres i ograniczenia

Lokalnie Rust 1.99.1, Miri commit 48f4b05538, Loom 0.7.2, Tokio 1.54.1.
Testy działają offline; lokalna baza advisories nie była odświeżana.
Miri i skończone modele nie dowodzą wszystkich zachowań sprzętu/FFI. Rozbieżność
Stacked/Tree Borrows jest jawnie eskalowana. Acme jest pełnym lokalnym dostawcą
referencyjnym, bez twierdzeń o rzeczywistym SDK lub trwałości po awarii.
Nowa wiedza nie zmienia obowiązkowych testów Miri/aliasowania, async ani Loom.
