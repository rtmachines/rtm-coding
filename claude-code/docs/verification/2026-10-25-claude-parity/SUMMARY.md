# Claude Code: zgodność workflow i wyniki regresji

Data: 2026-10-25. Wynik końcowy: **PASS — 49/49 kontroli automatycznych,
11/11 świeżych review oraz 11/11 niezależnych ocen dowodów**.

## Zakres zmiany

Wersja Claude Code otrzymała wymagania dowodowe obecnego workflow Codex:

- wiedzę z przypiętej, lokalnej kopii `rtmachines/rust-skills`,
- celowane testy Miri i oddzielną analizę aliasowania dla unsafe/FFI,
- testy deadlocków, anulowania i zakończenia zadań oraz modele Loom dla synchronizacji,
- sprawdzanie rzeczywistej dostępności LSP i raportowanie jego użycia,
- opcjonalny reviewdog, który nie może zamienić błędu Clippy w PASS,
- rozdzielenie APPROVE, REQUEST_CHANGES, ESCALATE i INCOMPLETE,
- walidację raportu przez natywne hooki oraz instalator zachowujący dodatkowe pliki
  i ustawienia użytkownika.

Brak raportu, nieukończony model i brak wymaganych dowodów nie są traktowane jako PASS.
Automatyczna kontrola formatu i pochodzenia raportu jest oddzielona od oceny jakości
jego argumentów oraz wykonanych prób.

## Tożsamość próby

- Workflow i wejścia: `accbf87cfed35bfbb1c90b2d2855bf65c8bd9748506b490e67b3d164081c2a3c`.
- Runtime: rzeczywisty lokalny **Claude Code 2.1.308**.
- Model zapisany w sesjach: `claude-sonnet-5-5`, odziedziczony z ustawień użytkownika.
- Każdy z 11 raportów pochodzi z osobnej natywnej sesji Claude; zachowano transkrypty,
  identyfikatory sesji oraz hashe raportów i wejść.
- Każde repo testowe korzystało z własnego katalogu kompilacji.

## Wyniki świeżych review

| Przypadek | Decyzja | Ocena |
|---|---|---|
| 01: sześć błędów logiki, w tym dirty i untracked | REQUEST_CHANGES | PASS |
| 02: poprawna kontrola logiki | APPROVE | PASS |
| 03: unsafe/FFI, deadlock, anulowanie, shutdown, atomiki | REQUEST_CHANGES | PASS |
| 04: przeoczony wcześniej problem aliasowania Box | REQUEST_CHANGES | PASS |
| 05: brak kontraktu quiescence dostawcy FFI | ESCALATE | PASS |
| 06: poprawna kontrola pamięci i współbieżności | APPROVE | PASS |
| 07: nieukończona eksploracja Loom | ESCALATE | PASS |
| 08: nierozstrzygnięte anulowanie u dostawcy | ESCALATE | PASS |
| 09: zamknięcie eskalacji po ukończeniu modelu | APPROVE | PASS |
| 10: zamknięcie po kontrakcie i testach implementacji dostawcy | APPROVE | PASS |
| 11: sam kontrakt bez implementacji dostawcy | ESCALATE | PASS |

PASS w tej tabeli oznacza poprawną reakcję workflow na dany przypadek, także wtedy,
gdy badany kod zawiera celowy błąd. Nie oznacza zatwierdzenia wszystkich repozytoriów.

W przypadku 04 Miri wykazało problem aliasowania w obu sprawdzanych modelach.
W przypadku 09 model Loom zakończył wszystkie sześć przeplotów przewidzianych
przez ten mały model. W przypadku 10 dowody objęły anulowanie przez timeout
i porzucenie future przed oraz po zatwierdzeniu operacji przez dostawcę.

## Pozostałe kontrole

Przeszły wspólne kontrakty Claude/Codex, próby izolujące błędy reviewdog,
35 testów hooków, 10 testów instalatora oraz testy powiązania raportów z wejściami,
wspólnego runnera i bramki CI. Logi zachowano w `verification-logs/`.

Osobny test rzeczywistego hosta potwierdził blokowanie niepełnego raportu przez
hook Stop i przyjęcie kompletnego raportu INCOMPLETE. Test komendy
`/rust-pr-review origin/main` potwierdził uruchomienie agenta i zwrot INCOMPLETE
przy celowo zabronionym Cargo. Te próby transportu nie zastępują 11 świeżych review.

Zmodyfikowano konfigurację automatycznych regresji GitHub Actions. Ta próba jest
lokalna: nie publikowano zmian ani nie uruchamiano nowego workflow na GitHubie.
Istniejąca bramka świeżych raportów Codex zachowuje własny format dowodów.

## Ograniczenia i uwagi z audytu

LSP było niedostępne w badanych sesjach i raporty prawidłowo zapisały ten fakt.
Próba nie potwierdza integracji z działającym natywnym serwerem LSP.

Niezależny audyt sprawdził argumenty, komendy, wyniki, zgodność kopii źródeł oraz
pochodzenie raportów. Zachował również drobne zastrzeżenia: nieprecyzyjny opis
liczby usterek i częściowe pokrycie jednej asercji w przypadku 01, słabszy test
pomocniczy cyklu życia zadań w przypadku 04 oraz opis braku dowodu jako P1/spec FAIL
w przypadku 11. Nie podważają one wykazanych usterek ani wymaganych decyzji.
Szczegóły są w [ocenie dowodów](semantic-assessment.json).

## Zachowane materiały

- [Paczka źródeł, raportów, transkryptów i logów](claude-review-evidence.tar.gz)
  — bez katalogów Cargo target i pamięci podręcznej.
- [Manifest archiwum z SHA-256](archive-manifest.json).
- [Wyniki kontroli automatycznych](diagnostics.json).
- [Akceptacja świeżych raportów](review-results.json).
- [Niezależny audyt dowodów](semantic-assessment.json).
- [Wynik natywnego wywołania komendy](verification-logs/native-slash-status.json).
- [Historia prób i usuniętych problemów](development-notes.md).

Raporty końcowe znajdują się w `reports/01/report.md` do `reports/11/report.md`.
Wcześniejsze nieudane lub nieaktualne próby pozostają opisane jako takie;
nie zostały przemianowane na aktualne dowody PASS.
