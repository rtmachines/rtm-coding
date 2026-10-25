# rtm-coding

Workflow review Rust dla Codex i Claude Code. Oba warianty wymagają dowodów
adekwatnych do zmiany: Miri i analizy aliasowania dla unsafe/FFI, testów deadlocków,
anulowania i zakończenia zadań oraz modeli Loom dla synchronizacji. Nierozstrzygnięte
ryzyka prowadzą do ESCALATE, a brak zwykłych wymaganych kontroli do INCOMPLETE.

| Środowisko | Instalacja i instrukcja |
|---|---|
| Codex | [skille w `skills/`](skills/README.md) |
| Claude Code | [pakiet w `claude-code/`](claude-code/README-CLAUDE.md) |

Instalacja Claude Code z katalogu tego repozytorium:

```sh
bash claude-code/install.sh --claude /ścieżka/do/projektu-rust
```

Następnie w Claude Code, w projekcie Rust:

```text
/rust-pr-review origin/main Sprawdź zgodność z REQUIREMENTS.md.
```

Pakiet zawiera agenta, hooki walidujące raport, przypiętą lokalną bazę `rust-skills`
i opcjonalny reviewdog. Raport wskazuje, czy rzeczywiście użyto LSP.
Szczegóły wymagań, instalacji i konfiguracji są w instrukcji wariantu.

## Testy i dowody review

[Opis CI](tests/README.md) rozdziela kontrole automatyczne od weryfikacji raportów.
Obie wymagane kontrole obejmują wariant Codex i Claude. Brak lub nieaktualność
dowodów blokuje akceptację. GitHub Actions nie uruchamia płatnych sesji modeli.

[Weryfikacja Claude z 2026-10-25](claude-code/docs/verification/2026-10-25-claude-parity/SUMMARY.md)
zawiera 49 kontroli automatycznych, 11 rzeczywistych review Claude Code,
niezależne oceny dowodów i pełną paczkę raportów. CI ponownie wykonuje automatykę
i porównuje aktualne wejścia z wejściami tych review.

`claude-code/` jest samodzielnym, zamrożonym zestawem z własnym fingerprintem.
Kopie zasobów Codex wewnątrz niego obsługują testy zgodności między wariantami;
publiczne skille Codex pozostają w `skills/`. Taki podział zachowuje oryginalne
powiązania obu paczek dowodów z testowanymi wersjami. Zagnieżdżony plik
`claude-code/.github/workflows/` jest częścią zamrożonego zestawu; aktywny workflow
repozytorium znajduje się w głównym `.github/workflows/`.
