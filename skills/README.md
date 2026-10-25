# Skille Rust dla Codex

- `rust-pr-review`: review zmian Rust, bramki Cargo i opcjonalny reviewdog,
  wymagane dowody Miri/aliasowania oraz testy async i modele Loom.
- `rust-best-practices`: wymagany podręcznik pomocniczy Apollo (MIT).

## Instalacja w projekcie

Z katalogu tego repozytorium skopiuj oba foldery do `.agents/skills/` projektu Rust:

```bash
mkdir -p /ścieżka/do/projektu/.agents/skills
cp -R skills/rust-pr-review skills/rust-best-practices /ścieżka/do/projektu/.agents/skills/
```

Przy aktualizacji sprawdź wcześniej lokalne zmiany w istniejących skillach.
Otwórz projekt w Codex i wywołaj:

```text
Użyj $rust-pr-review. Zrób review względem origin/main, także zmian lokalnych
oraz plików untracked. Nie poprawiaj kodu. Możesz wykonywać izolowane testy
poza repozytorium. Zapisz raport w /tmp/rust-review.md.
```

Dostarcz wymagania zadania oraz projektową politykę REVIEW.md (obsługiwane features,
toolchain, wymagane kontrole). Przygotuj deny.toml zgodnie z polityką zależności.
Skille nie instalują narzędzi: wymagane Cargo, rustfmt, Clippy i cargo-deny;
Miri oraz Loom stosuje się do odpowiednich ścieżek bezpieczeństwa i współbieżności.
Brak wymaganych dowodów blokuje APPROVE. Reviewdog jest opcjonalny:

```bash
RUST_REVIEWDOG=1 bash .agents/skills/rust-pr-review/scripts/gates.sh
```

Licencje materiałów zewnętrznych znajdują się w folderach skilli.
