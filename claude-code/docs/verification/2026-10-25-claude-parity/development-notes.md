# Przebiegi rozwojowe Claude Code

Poniższe próby ujawniły problemy podczas wdrażania. Nie są paczką świeżych raportów
końcowej wersji i nie zostały przepisane na nowy fingerprint.

- Analiza starego kontraktu przez odseparowanego agenta Codex: dopuszczone APPROVE
  przy spec PARTIAL oraz nadmierna eskalacja po zamknięciu dowodów. Była to analiza
  tekstowa, nie wykonanie w Claude Code.
- Rzeczywisty Claude Code 2.1.308: Stop z exit 2 nie zatrzymał wyniku DONE.
  Jawne JSON decision:block z exit 0 zatrzymało wynik i wymusiło kompletny raport.
  Stały test natywny rozróżnia te przypadki i nie zalicza samego exit 0 jako sukcesu.
- SubagentHandback: walidacja przed dostarczeniem raportu; po dostarczeniu Stop
  sprawdza ostatnią udaną parę tool_use/tool_result w transkrypcie. Format sprawdzony
  także na rzeczywistych zdarzeniach natywnego agenta.
- Pierwsza poprawna kontrola logiki została oceniona zbyt zachowawczo: niejasny
  kontrakt znaku plus w parse_limit i mieszanie braku testów w repo z dowodem
  wykonanym w izolowanym katalogu. Doprecyzowano kontrakt fixture jako u16::from_str
  oraz rozdzielono kompletność dowodów od miejsca zapisu testów.
- Guard blokował zmienne ścieżki logów, heredoki i operatory w kodzie prób jako
  rzekome zmiany źródła. Wszystkie 13 zaobserwowanych fałszywych blokad odtworzono
  i naprawiono. Złożone polecenia podlegają zwykłym uprawnieniom Claude Code.
- Review kodu wykryło lukę fingerprintu wejść: druga zmiana już zmodyfikowanego
  manifestu lub kontraktu nie zmieniała git status. Nowa migawka Claude obejmuje
  treść i tryb wszystkich plików widocznych dla Git, a nie tylko src/ i tests/.
- Awaria jq w formaterze decyzji hooka dawała pusty sukces. Dodano stały JSON
  blokujący generowany przez Bash, niezależnie od dostępności jq.

Stare przebiegi pozostają w /tmp/claude-parity-runtime/ i
/tmp/claude-parity-release-20261025/. Bramka prawidłowo odrzuciła je po zmianie
workflow lub testów. Wynik końcowy jest opisany osobno w SUMMARY.md.

## Odrzucenie paczki mimo poprawnych werdyktów

Przebieg /tmp/claude-parity-final-review-20261025 uzyskał 49/49 automatycznych
kontroli i 11/11 zgodnych werdyktów, lecz tylko 8/11 ocen jakości dowodów.
Brak rzetelnych dowodów zatrzymał całą bramkę (exit 1):

- 03: raport podał dwie próby jednostkowe, podczas gdy log zwykłych testów pokazywał
  zero. Celowane próby nadal poprawnie wykryły sześć mechanizmów błędów.
- 04: wykrycie aliasowania było prawdziwe, lecz próbę podejrzaną o UB uruchomiono
  także natywnie, a efekt po pending() w teście zakończenia zadania był nieosiągalny.
- 10: brak timeoutu rzeczywistego dostawcy przed commit, wymaganego przez kontrakt,
  mimo zadeklarowanego zamknięcia eskalacji.

Doprecyzowano obowiązek ponownego audytu logów, macierz scenariuszy kontraktu,
sprawdzanie, czy próby zakończenia zadań mogą wykryć błąd oraz rozdzielenie prób Miri od natywnych.
Kolejny przebieg używa także oddzielnych domyślnych katalogów Cargo target dla
repozytoriów; poprzedni sterownik testowy współdzielił katalog między procesami.
Tej odrzuconej paczki nie przeniesiono na nowy fingerprint.

Po audycie dopracowano także dodatnią kontrolę 02: poprawna implementacja nie miała
testów regresyjnych wymaganych przez własną politykę projektu. Wariant Claude
otrzymuje teraz sześć rzeczywistych testów w repozytorium; oczekiwane APPROVE
pozostało bez zmian. Kolejny przebieg uruchomiono na dysku z osobnymi katalogami
kompilacji, ponieważ stare artefakty zapełniły /tmp. Usunięto wyłącznie wygenerowane
katalogi Cargo target należące do tej pracy. Uszkodzone lub przestarzałe transkrypty
nie przeszły weryfikacji i nie wchodzą do końcowej paczki.
