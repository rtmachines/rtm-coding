# Test ochrony main

Test integracyjny ochrony gałęzi wykonuje się na osobnym PR:

1. Zachowaj workflow i wejścia testowe; usuń bieżącą paczkę review z gałęzi testowej.
2. Poczekaj na wyniki Actions: automatyka powinna przejść, a fresh-reviews nie.
3. Spróbuj zwykłego scalenia dokładnie sprawdzonego commita, bez obejścia administratora.
   GitHub powinien odrzucić żądanie; sprawdź również, że PR nadal jest otwarty.
4. Przywróć dokładnie tę samą prawidłową paczkę. Poczekaj na oba wymagane statusy
   SUCCESS dla nowego commita i aktualną bazę main.
5. Scal zwykłym żądaniem z kontrolą SHA. Potwierdź stan MERGED i obecność paczki w main.

Nie zmieniaj ochrony gałęzi ani oczekiwanych wyników testów w trakcie próby.
Przywrócenie paczki pozostawia jej źródła i fingerprint bez zmian; dokumentacja
tego testu może pozostać jako jedyna końcowa zmiana PR.
