# Skille Rust dla Codex

Wersja dla Claude Code ma osobny [pakiet instalacyjny i instrukcję](../claude-code/README-CLAUDE.md).

- `rust-pr-review`: review zmian Rust, bramki Cargo i opcjonalny reviewdog,
  wymagane dowody Miri/aliasowania oraz testy async i modele Loom.
- `rust-skills`: główna baza wiedzy z `rtmachines/rust-skills`, 265 reguł (MIT),
  przypięta do commita `a1e290d53d43a85421ff16dde23b5f8ec0b48539`.
- `rust-best-practices`: uzupełniający podręcznik Apollo (MIT).

## Instalacja w projekcie

Z katalogu tego repozytorium skopiuj trzy foldery do `.agents/skills/` projektu Rust:

```bash
mkdir -p /ścieżka/do/projektu/.agents/skills /ścieżka/do/projektu/.agents/rust-review-kit
cp -R skills/rust-pr-review skills/rust-best-practices skills/rust-skills /ścieżka/do/projektu/.agents/skills/
cp tests/vendor/rust-review-kit/vendored.tsv /ścieżka/do/projektu/.agents/rust-review-kit/
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

Baza wiedzy jest dołączona lokalnie; review nie pobiera jej z sieci. Raport wskazuje
użytą rewizję i reguły. Porady nie zastępują wymagań projektu ani dowodów Miri/Loom.
