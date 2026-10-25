## Verdict: REQUEST_CHANGES
Все шесть контрактов из REQUIREMENTS.md нарушены, и каждое нарушение подтверждено исполняемой пробой (Miri, Tokio, Loom). Дополнительно падает clippy (`-D warnings`). Нерешённых эскалаций нет: дефекты доказаны, а не предполагаются.

## Tooling
- rust-lsp: UNAVAILABLE (в этой среде нет ни нативного LSP, ни MCP-интеграции rust-lsp/code-review-graph; зондирование рабочего пространства невозможно)
- lsp-used: NO
- lsp-evidence: инструменты LSP/графа не предоставлены; семантических запросов не было. Использованы Read/Grep/Bash и чтение исходников (129 строк в src/).
- lsp-limitations: граф и семантическая навигация не использовались; объём крошечный (5 файлов), весь код прочитан целиком, поэтому пробел минимален. Знания: rust-skills (revision a1e290d53d43a85421ff16dde23b5f8ec0b48539 по vendored.tsv, без локальных правок для прочитанных правил); прочитаны unsafe-safety-comment, conc-atomic-ordering, async-cancel-safety плюс MEMORY-VALIDATION, CONCURRENCY-VALIDATION, SPEC-PASS.

## Gates
- fmt: PASS (cargo fmt --all -- --check, exit 0; fmt.log)
- clippy: FAIL (cargo clippy --offline --workspace --all-targets --locked -- -D warnings, exit 101: clippy::boxed_local at src/registration.rs:15; clippy.log)
- tests: PASS (cargo test --offline --locked --no-fail-fast, exit 0: 2 passed — service::tests::snapshot_initial, approved_delivery; 0 doctests; test.log). Проходящие тесты не покрывают ни один из контрактов.
- doctests: N/A (включены в cargo test; 0 doctests выполнено)
- deny: PASS (cargo deny --locked --offline check, exit 0: advisories ok, bans ok, licenses ok, sources ok; предупреждение license-not-encountered для BSD-3-Clause. Свежесть: офлайн, используется локальная копия advisory-db без обновления — новые advisory могли быть не учтены)

## Memory safety
- memory-scope: REQUIRED (src/bytes.rs read_word; src/registration.rs Registration::new/Drop)
- miri: FAIL (nightly cargo-miri 0.1.0 48f4b05538 2026-10-23; 3 целевые пробы, все дали Undefined Behavior)
- aliasing: FAIL (retained pointer указывает на освобождённый Box, см. ниже)
- memory-evidence: изолированная копия в reviews/03/probe (хэши src/Cargo.* идентичны исходным, probe-source-hashes.txt vs source-hashes.txt). Сначала `cargo +nightly check --tests` (exit 0, без запуска), затем `cargo +nightly miri test --offline --locked --test <t>`. mem_read_word::short_input_three_bytes: "attempting to access 4 bytes, but got ... only 3 bytes" (src/bytes.rs:7; miri-read-word.log). mem_read_word::unaligned_input: "pointer with alignment 1, but alignment 4 is required" (miri-unaligned.log). mem_registration::consumer_reads_after_constructor_returns (шим соблюдает контракт: читает диапазон, пока Registration жива): "alloc has been freed, so this pointer is dangling" (miri-registration.log). Нативно UB-пробы не запускались.
- aliasing-evidence: Registration::new принимает `Box<[u8]>` по значению, передаёт `bytes.as_ptr()` в register, затем `bytes` уничтожается на выходе из функции — аллокация освобождена, пока потребитель по контракту ещё может читать до unregister. Владение не сохраняется в Registration (поле только len). read_word: `as_ptr().cast::<u32>().read()` требует выравнивания 4 и ≥4 валидных байт; ни то ни другое не проверяется. Закрытие: хранить Box в Registration (до unregister) и использовать `read_unaligned` с проверкой `len >= 4` (кандидаты, не проверены).

## Concurrency
- async-scope: REQUIRED (src/service.rs: increment_and_snapshot, approved_pop, stop_worker)
- deadlocks: FAIL (async_probe::increment_progress, current_thread, timeout 300 мс: "did not complete (self-deadlock)")
- cancellation: FAIL (async_probe::cancel_before_approval_preserves_queue: очередь пуста после отмены до approval — элемент потерян)
- task-lifecycle: FAIL (async_probe::stop_worker_waits: воркер, припаркованный на oneshot, выполнил эффект после возврата stop_worker; контроль stop_worker_control_abort_await проходит, значит проба не вакуумна)
- async-evidence: `cargo test --offline --locked --test async_probe` в probe/: 4 теста, 1 passed (контроль), 3 failed, exit 101 (async-probe.log). Tokio =1.54.1, current_thread, явные yield_now вместо sleep для воркера.
- sync-scope: REQUIRED (src/publication.rs Published — кастомный протокол публикации через атомики)
- loom: FAIL (`--features model`, LOOM_MAX_PREEMPTIONS=3, loom 0.7.2; тест observed_some_equals_value: assertion left 0 right 42; loom-probe.log). Используются реальные типы Published (cfg-подмена на loom::sync::atomic), контракт single-writer соблюдён: один писатель, один читатель.
- synchronization: FAIL (publish: value.store(Relaxed), ready.store(Relaxed); snapshot: ready.load(Relaxed) затем value.load(Relaxed) — нет release/acquire, отношения happens-before нет, читатель может увидеть ready=true и value=0. Нужны Release на ready.store и Acquire на ready.load.)
- model-evidence: src Published без изменений; модель — 2 потока (писатель/читатель), одна модель loom::model; инвариант: Some(v) ⇒ v == 42; контрпример найден, поэтому полнота исследования не требуется для FAIL.

## Spec
- spec: FAIL (REQUIREMENTS.md)
- missing: read_word для <4 байт возвращает None (только пустой срез); Registration не удерживает буфер; Service не завершает инкремент; approved_pop не безопасен при отмене; stop_worker не ждёт воркера; Published не даёт гарантии наблюдаемого значения.
- unrequested: нет.
- contradictions: см. Findings (6 прямых противоречий требованиям).

## Findings
- [P1] src/bytes.rs:7 - read_word проверяет только `is_empty()`, а не `len() < 4`, и читает `u32` через `.cast::<u32>().read()` (требует align 4). Trigger: срез из 1–3 байт или невыровненный срез. Impact: UB (чтение за границей, невыровненный доступ), нарушает "arbitrary alignment" и "None для менее четырёх байт"; Miri подтверждает оба случая. Fix: `if bytes.len() < 4 { return None }` и `read_unaligned` (или `u32::from_ne_bytes(bytes[..4].try_into().ok()?)` без unsafe).
- [P1] src/registration.rs:15 - `Box<[u8]>` уничтожается при выходе из `new`, но указатель передан в register и должен жить до unregister. Trigger: любой потребитель, читающий диапазон после возврата конструктора. Impact: use-after-free; нарушает "retains buffer ownership until unregister completes"; clippy::boxed_local указывает на ту же причину; Miri: freed allocation. Fix: хранить `bytes: Box<[u8]>` в Registration и освобождать после вызова unregister в Drop.
- [P1] src/service.rs:16 - `increment_and_snapshot` держит guard `count` и вызывает `self.snapshot()`, повторно захватывая тот же неreentrant tokio Mutex. Trigger: любой вызов. Impact: вечное ожидание (self-deadlock), проба подтверждает. Fix: прочитать `*count` под уже взятым guard и вернуть значение либо отпустить guard перед snapshot.
- [P1] src/service.rs:25 - `approved_pop` делает `pop_front()` до ожидания approval. Trigger: drop future до получения approval (или закрытый sender). Impact: элемент безвозвратно удалён; нарушает "consumes nothing if cancelled". Fix: сначала `approval.await.ok()?`, затем взять lock и pop (либо peek + pop после approval).
- [P1] src/service.rs:32 - `stop_worker` делает `drop(worker)`, что только отсоединяет задачу. Trigger: любой вызов, воркер ещё жив. Impact: воркер продолжает работу и имеет побочные эффекты после возврата. Fix: `worker.abort(); let _ = worker.await;` (для блокирующей/кооперативной остановки — сигнал + await); проверить кандидата отдельным тестом.
- [P1] src/publication.rs:23 - все операции `Ordering::Relaxed`. Trigger: читатель видит ready=true раньше value. Impact: наблюдается Some(0) вместо опубликованного значения; Loom контрпример. Fix: `ready.store(true, Release)` и `ready.load(Acquire)` (value остаётся Relaxed); перепроверить Loom.
- [P2] src/service.rs:36 - тесты покрывают только начальный snapshot и happy-path approved_pop; нет тестов для deadlock, отмены, остановки, Miri, Loom. Fix: добавить пробы из reviews/03/probe/tests как регрессионные.

## Residual risks
- Scope: base origin/main = fcd0f85b00baa7a8caa47007d8c5d6438e5fac9f, head = 859a0b2ec84b2c702d1e398ff89b364c383f24f1; рабочее дерево чистое (status-tree.txt пуст), неотслеживаемых файлов нет. Продуктовый diff: src/*.rs (129 строк), Cargo.toml, .gitignore; остальное — установленные .claude/ инструменты и документы, не ревьюились построчно. Хэши в source-hashes.txt.
- Исправления в разделе Findings — кандидаты, не проверены.
- LSP/граф недоступны; deny выполнен офлайн (advisory-db может быть устаревшей); Loom-модель ограничена 3 вытеснениями (для FAIL достаточно); Miri не доказывает отсутствие UB в исправленном коде; сторонние FFI-гарантии (потоки, unwinding) не проверялись.
- Артефакты: reviews/03 (status.txt, *.log, probe/, report.md).
