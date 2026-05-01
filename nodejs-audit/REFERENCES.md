# REFERENCES — Annotated Bibliography

> Каждая фаза цитирует **конкретную книгу + главу**. Это переводит «мне кажется» в «это известный анти-паттерн, описан там-то». Перед ревью PR владелец имеет право спросить «на чём это основано» — этот файл отвечает.

---

## Каноны DDD и архитектуры

### Eric Evans — *Domain-Driven Design: Tackling Complexity in the Heart of Software* (2003)
- **§4 Isolating the Domain** — почему `entities/` должны стать domain (не repositories).
- **§6 Aggregates** — где живут invariants.
- **§14 Maintaining Model Integrity** — Anti-Corruption Layer для каждой external integration.

### Vlad Khononov — *Learning Domain-Driven Design* (2021)
Самый практичный из DDD-книг для TS/JS.
- **§3 Managing Domain Complexity** — Core / Supporting / Generic subdomains.
- **§7 Modeling the Dimension of Time** — event sourcing для денежных операций.
- **§8 Architectural Patterns** — Layered vs Hexagonal vs CQRS.

### Vaughn Vernon — *Implementing Domain-Driven Design* (2013) + *Strategic Monoliths and Microservices* (2024)
- **IDDD §1-3** — bounded context map.
- **IDDD §8 Domain Events** — основа event bus.
- **Strategic §3** — когда extract microservices, а когда нет.

### Robert C. Martin — *Clean Architecture* (2017)
- **§22-24 Boundary** — почему `domain/` не должен импортировать `infrastructure/`.
- **§16 Independence** — developer-time vs deployment independence.

### Mark Richards & Neal Ford — *Fundamentals of Software Architecture* 2e (2025)
- **§5 Architecture Characteristics** — 8 «ilities» как метрики.
- **§6 Identifying Architectural Characteristics** — fitness functions как код.
- **§16 Component-Based Thinking** — границы между компонентами.

### Neal Ford et al. — *Building Evolutionary Architectures* 2e (2023)
- **§2 Fitness Functions** — каждый ADR = executable test.
- **§5 Evolutionary Data** — schema migrations как evolution.
- **§6 Building Evolutionary Architectures** — incremental refactor protocol.

---

## Distributed systems / scaling

### Sam Newman — *Building Microservices* 2e (2021) + *From Monolith to Microservices* (2019)
- **BM §4 Integration** — Anti-Corruption Layer.
- **BM §13 Reliability** — circuit breaker, bulkheads, timeouts.
- **From Monolith §1-3** — strangler fig pattern.

### Martin Kleppmann — *Designing Data-Intensive Applications* (2017, 2e expected)
- **§1 Reliability** — fault tolerance contract.
- **§4 Encoding and Evolution** — zero-downtime schema migrations.
- **§7 Transactions** — saga pattern, idempotency keys.
- **§11 Stream Processing** — domain events bus, transactional outbox.

### Susan Fowler — *Production-Ready Microservices* (2016)
- 8 production-readiness pillars: stability, reliability, scalability, fault-tolerance, performance, monitoring, documentation, understandability.
- Чек-лист на каждый deploy.

---

## Observability

### Charity Majors, Liz Fong-Jones, George Miranda — *Observability Engineering* (2022)
- **§3 High-cardinality events** — structured events с per-request fields.
- **§5 Distributed tracing** — OpenTelemetry стандарт.
- **§7 SLOs** — error budget driven development.

### Betsy Beyer et al. — *Site Reliability Engineering / SRE Workbook* (Google, 2018)
- SLI/SLO/SLA framework.
- Toil reduction — что автоматизировать первым.

---

## Testing

### Vladimir Khorikov — *Unit Testing: Principles, Practices, and Patterns* (2020)
- **§2 What is a unit test?** — London (mocks) vs Detroit (state).
- **§5 Mocks and test fragility** — mocks for adapters, не для domain.
- **§7 Refactoring towards testability** — практические шаги.

### Michael Feathers — *Working Effectively with Legacy Code* (2004, ✅ canon)
- **§4 The Seam Model** — где seam-точки в codebase.
- **§13 Characterization tests** — фиксация существующего поведения перед рефактором.

---

## Functional / error handling

### Scott Wlaschin — *Domain Modeling Made Functional* (2018)
- **§3 Type-driven design** — модель для `Result<T, E>`.
- **§9 Validating an Order** — декомпозиция use case в pure functions.

### Yegor Bugayenko — *Elegant Objects* vol. 1-2 (2017)
- Anti-anemic models — entities должны иметь поведение.
- Immutability — value objects.

---

## Coupling, cohesion, fragility

### Adam Tornhill — *Your Code as a Crime Scene* 2e (2024)
- **§3 Hot-spots** — `churn × complexity` = fragility.
- **§7 Coupling** — temporal vs structural.
- **Используется в Phase 4** для hot-spot матрицы.

### John Ousterhout — *A Philosophy of Software Design* 2e (2021)
- **§4 Modules Should Be Deep** — narrow API, deep impl.
- **§5 Information Hiding** — где `as any` пробивает абстракции.
- **§19 Software Trends** — functional core / imperative shell.

### Donella Meadows — *Thinking in Systems* (2008)
- Feedback loops, leverage points — почему refactor одного hot-spot даёт больше эффекта, чем 5 косметических.

---

## Integration patterns

### Gregor Hohpe & Bobby Woolf — *Enterprise Integration Patterns* (2003, canon)
- **§7 Message Construction** — typed events.
- **§10 Routing** — content-based router.
- **§12 Endpoint** — transactional client, dead-letter channel.

### Gregor Hohpe — *The Software Architect Elevator* (2020)
- Trade-off communication между tech и business — для написания ADR.

---

## TypeScript / Node specifics

### Khalil Stemmler — *Domain-Driven Design with TypeScript* (online series)
- TS-specific recipes для DDD-патернов.

### Matthias Noback — *Object Design Style Guide* (2019)
- TS-friendly правила про immutability, value objects, command/query separation.

---

## Security baselines

### **OWASP Top 10 (2021)** + **OWASP ASVS 4.0**
- Phase 7 (Security) использует ASVS как чек-лист по уровням (L1, L2, L3).

### **The Twelve-Factor App** (12factor.net)
- Конфиг через env, processes как stateless, port binding — стандарт baseline.

---

## Mapping: фаза → книги

| Фаза | Главные источники |
|---|---|
| 0 Bootstrap | 12factor §3 (Config) |
| 1 MCP probe | — |
| 2 Recon | Ousterhout §4-5 (для оценки модулей) |
| 3 Deterministic | Feathers §4 (seams) |
| 4 Hot-spots | **Tornhill §3, §7** (главная книга фазы) |
| 5 Architecture (DDD) | **Evans §4-6, §14**, **Khononov §3, §7-8**, **Martin §22-24** |
| 6 Readability | **Ousterhout §4-5, §19**, Bugayenko |
| 7 Security | **OWASP ASVS L1-L2**, OWASP Top 10 (2021), 12factor §3 |
| 8 Performance | **Kleppmann §1, §7, §11**, Newman BM §13 |
| 9 Observability | **Majors §3, §5, §7**, Beyer SRE |
| 10 AI-readability | Ousterhout §4-5, Sandi Metz (TRUE), Khorikov §7 |
| 11 Synthesis | **Richards/Ford §5-6** (10 ilities), **Ford Evolutionary §2** (fitness) |
| 12 Production roadmap | **Fowler PRMS** (8 pillars), **Newman From Monolith §1-3**, Hohpe SAE |

---

## Правило применения

> Перед стартом фазы — прочесть **минимум 1 главу** из её ключевой книги.
> Без этого PR на ADR-DRAFTS отклоняется на review.

Если у владельца нет физических книг — кратких summary достаточно (Goodreads / O'Reilly excerpt). Цель — **общий словарь между ИИ-агентами**, а не academic rigor.

---

## Не использовать как primary source

- ~~GoF *Design Patterns* (1994)~~ — patterns ok, но imperative-focused; используйте только как глоссарий.
- ~~*Clean Code* (Martin, 2008)~~ — много spurious advice; читайте только §1-3, §6.
- ~~Spring/Java-only книги~~ — не наш стек.

---

<div align="center">

[← MASTER_PROMPT](./MASTER_PROMPT.md) ·
[AUDIT.md (индекс)](./AUDIT.md) ·
[Audit Pipelines](../README.md)

</div>
