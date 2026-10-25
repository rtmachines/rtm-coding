# CI: automatyka i świeże review

Workflow `.github/workflows/workflow-regressions.yml` dotyczy samego kitu. Nie zmienia
szablonu CI instalowanego w ocenianych aplikacjach. Uruchamia się dla pull requestów,
push do main i ręcznie. Nie filtruje ścieżek: oba wymagane statusy są obecne także
przy PR dokumentacyjnym. GitHub pozostawia pominięte przez paths wymagane workflow w
Pending, a pominięty job może raportować sukces; dlatego bramka review ma `always()`
i jawnie sprawdza wynik poprzednika. [Dokumentacja zdarzeń i warunków](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Dwa statusy

- `workflow-regressions / automatic`: instaluje przypięty Rust i Miri, cargo-deny,
  pobiera zależności/advisories w fazie przygotowania, a następnie wykonuje offline
  kontrole automatyczne. Zapisuje wejścia Git, polecenia review i logi w artefakcie
  `workflow-regression-inputs` (run.tar.gz). Zielony status dotyczy wyłącznie automatyki.
- `workflow-regressions / fresh-reviews`: działa zawsze po pierwszym jobie. Nieudana,
  anulowana lub pominięta automatyka blokuje ten job. Brak paczki, dowodów, raportów
  albo oceny semantycznej nigdy nie daje kodu 0. Częściowe/stare wyniki nie są sukcesem.
  Job nie uruchamia LLM ani nie udaje, że dokonał review na podstawie testów.

Po opublikowaniu konfiguracji ustaw oba powyższe joby jako wymagane w regułach gałęzi.
Sam plik YAML nie ustawia ochrony gałęzi. Nie korzystamy z pull_request_target, sekretów
modelu ani uprawnień zapisu. CI nie publikuje komentarzy i nie uruchamia kodu z paczki
review; traktuje ją jako dane do walidacji.

## Dostarczenie świeżych raportów

1. Pobierz `workflow-regression-inputs` z przebiegu danego kodu. Rozpakuj run.tar.gz
   do nowego katalogu przez `tarfile.extractall(..., filter='data')`; zachowaj katalog
   `run/` razem z Git i metadanymi. Użyj tej samej wersji kitu w lokalnym checkout.
2. Zleć review na podstawie `run/review-requests.json`, wskazując **lokalne** ścieżki
   odpowiadające rozpakowanym repozytoriom i katalogom wyjściowym. Zachowaj zasady
   niezależności z tests/workflow/README.md. Ścieżki zapisane w requestach pochodzą
   z runnera CI i trzeba je przemapować. Wymagane narzędzia graph/LSP zapewnia środowisko
   reviewerów; nie są potrzebne do mechanicznej bramki w GitHub Actions.
3. Zapisz reports/logs w run/reviews/ID oraz ocenę dowodów w semantic-assessment.json.
   Nie edytuj wejść ani wyników diagnostyk. Uzupełnione braki muszą wynikać z nowego
   wykonania review, nie z ręcznej zmiany Verdict.
4. Zweryfikuj i wyeksportuj:

```sh
python tests/run-workflow-regressions.py /lokalna/sciezka/run --phase assess
python tests/workflow/ci/manage.py export /lokalna/sciezka/run
```

Eksporter tworzy `tests/workflow/review-evidence/<fingerprint>/`. Dodaj cały ten katalog
   do PR. Push ponownie uruchomi CI: automatyka odtwarza takie same wejścia, a bramka
   odczytuje odpowiadającą im paczkę. Bez raportów pierwszy przebieg ma celowo czerwony
   job fresh-reviews; nie ma continue-on-error ani `|| true` wokół jego wyniku.

Fingerprint obejmuje źródła workflow, skrypty, testy, konfigurację CI, przypięte
narzędzia, instalator, licencje i używane zamrożone archiwa. Historyczne wyniki oraz
katalog paczek review są wyłączone. Dodanie samej paczki nie unieważnia jej własnego
hasha. Każda zmiana objętego pliku wymaga nowej paczki. Dodatkowo wiążemy pełne
inputs.json (źródła, status working tree i HEAD 11 repozytoriów). Commity przygotowania
mają deterministyczne metadane, więc identyczna wersja odtwarza te same wejścia na
kolejnym runnerze. Każdy plik dowodu ma sprawdzaną sumę SHA-256.

To kontrola zgodności wersji i kompletności, nie podpis kryptograficzny autora ani
samodzielna ocena semantyczna raportu. Zatwierdzenie zawartości paczki i oceny dowodów
należy do normalnego review PR. Zestaw historycznych raportów nie jest kopiowany jako
„świeży”; nie eksportujemy automatycznie starych wyników pod nowym fingerprintem.
Paczka może być ponownie użyta tylko dla identycznego workflow i identycznych wejść.

## Narzędzia i diagnostyka

Wersje są w toolchains.json. Runner używa `MIRI_TOOLCHAIN` (lokalnie domyślnie nightly,
w CI przypięte wydanie). Bootstrap jest jedyną fazą korzystającą z sieci; po nim faza
regresji działa offline. Żaden cache nie zastępuje wyniku testów. Zmiana Miri wymaga
świadomego sprawdzenia oczekiwań eksperymentalnych modeli aliasowania.

`python tests/workflow/ci/test_ci.py` sprawdza brak raportu, brak oceny i pliku dowodu,
zmienione źródło, niepoprawny raport, stare powiązanie, uszkodzoną paczkę, niekompletne
kontrole oraz pełny obieg eksport/import. Zestaw zawiera 19 testów, w tym pięć
integracyjnych uruchamiających prawdziwe CLI eksportu i bramki na tymczasowym
repozytorium Git, bez podmieniania kontroli tożsamości ani oceny źródeł:

- zgodna paczka jest przyjmowana przez domyślne wyszukiwanie używane w CI;
- zmiana workflow odrzuca stary przebieg przed importem;
- po aktualizacji tożsamości przebiegu zmieniony workflow nadal odrzuca starą paczkę;
- zmiana źródła i manifestu wejść odrzuca starą paczkę;
- zmiana źródła przy starym manifeście kończy się błędem kontroli niezmienności.

Raport i diagnostyki tych pięciu testów są oznaczonymi sztucznymi danymi do testowania
mechanizmu akceptacji, nie świeżymi review Rust. Nie są publikowane jako dowody.
Istniejący krok „CI gate tests” uruchamia cały zestaw przed diagnostykami Rust.
Zmiana tych testów zmienia fingerprint workflow; wcześniejsza paczka pozostaje
historycznym dowodem i nie jest automatycznie przepisywana pod nową wersję.

`pack` zachowuje Git, ale wyklucza cache
kompilacji. Artefakty są przechowywane 14 dni; kompletne raporty zatwierdzone w repo nie
zależą od czasu przechowywania artefaktu.
