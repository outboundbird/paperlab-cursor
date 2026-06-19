# paperlab

`paperlab` is a multiagent system to help students to understand papers in machine learning and deep learning.

## Work flow


```mermaid
flowchart TB
    subgraph Learning["Learning suite — one paper at a time"]
        direction LR
        Acquirer((acquirer)) --> Sources[PDF / Git repo]
        Sources --> Dissector((dissector))
        Dissector --> Spec[spec.md]

        Spec --> Implementer((implementer))
        Sources -->|official code| Implementer
        Implementer --> CodeMap[code_map.md]
        Implementer --> DeepDive[code_map__slug__component.md]
        Implementer -.->|no code: draft| BPgate{critic<br/>blueprint-check}
        BPgate -.->|PASS| Blueprint[code_blueprint.md]
        BPgate -.->|FAIL x2| Escalate[escalate to user]

        Spec --> Coder((coder<br/>Stage 1))
        Blueprint --> Coder
        Coder --> VaultCode["code/ in vault<br/>method.py + test_invariants.py"]
        VaultCode -->|reconstructed source| Implementer

        Spec --> Critic((critic))
        CodeMap --> Critic
        Critic --> Review[critic_reviews.md]

        Spec --> Tutor((tutor))
        Tutor -. invokes .-> Explainer((explainer))
        Explainer --> ConceptBound[concept-slug.md]
        Tutor --> Concept[concept.md]
        Tutor --> Synth[synth__a__b.md]
        Tutor --> TutorLog[tutor_log.md / tutor_notes.md]
    end

    subgraph Experiment["Experimenter suite — many papers, one topic"]
        direction LR
        Experimenter((experimenter)) -. invokes .-> Comparator((comparator))
        Comparator --> Comparison[comparison.md]
        Experimenter --> Design[design.md + harness interface]
        Comparison -.-> Design
        Design --> Adapt((coder<br/>Stage 2 adapt))
        Adapt --> Methods[methods/ in sandbox]
        Methods --> Evaluator((evaluator))
        Evaluator --> Findings[findings.md]
    end

    Spec -. feeds .-> Experimenter
    VaultCode -. wrap to harness .-> Adapt
```

### Learning suite (one paper at a time)

`acquirer`, `dissector`, `implementer`, `critic`, `tutor`, plus the
backend `explainer`. The `acquirer` sets up the paper and the `dissector`
extracts `spec.md`; from there the `implementer` maps code, the `critic`
audits, and the `tutor` (the user-facing concept interface, `/tutor
<slug>`) explains — invoking the `explainer` in the background.

When a paper ships **no official code**, the `implementer`'s explicit,
opt-in **blueprint mode** reconstructs a framework-agnostic
implementation contract (`code_blueprint.md`) from the math. The draft is
gated **pre-emission** by the `critic`'s blueprint-check — the critic
re-derives the paper's math *independently* (the firewall) — and the file
is written only on PASS, else the implementer escalates after two retries.

The `coder`'s **Stage 1** (`/coder code <slug>`) then turns that
blueprint into reusable, runnable method code under `<vault>/<slug>/code/`
— `method.py` (a hybrid `Method` interface: paper-natural guts behind one
documented entry point) plus `test_invariants.py`, which emits the
blueprint's invariants as runtime assertions and runs them on synthetic
input (the **hop-2-vs-blueprint guard**). The method is coded once per
paper here and reused by every experiment that needs it.

The walkthrough then comes from the **same agent that documents official
code**: the `implementer` maps `method.py` against `spec.md` into a
`code_map.md` (its `reconstructed` source — identical format to the
official-code map), and the `critic` audits that map against the spec (a
**fidelity** audit: did the reconstruction drift from the paper?). So a
no-code paper ends up with the same `code_map.md` + `critic_reviews.md`
as a code-having one. Two firewalled checks bracket the reconstruction:
the critic guards the blueprint pre-emission (hop 1), and the critic
audits the resulting `code_map` against the spec (hop-2-vs-spec) — neither
performed by the agent that authored the artifact under review.

### Experimenter suite (many papers, one topic)

```mermaid
flowchart TB
    User([User: /experimenter topic]) --> StateCheck{Filesystem state<br/>under experiments/topic}

    StateCheck -->|no design.md| Plan
    StateCheck -->|design.md, no results| PlanResume[Plan-resume<br/>pick up dialogue]
    StateCheck -->|design.md + results| BuildEval

    subgraph Plan["Plan phase — open prose dialogue"]
        direction TB
        P1[research type emerges<br/>methods comparison / ablation /<br/>reproduction / sensitivity / exploration]
        P2[member set, criterion,<br/>data-synthesis design,<br/>seam 5.2 if multi-method]
        P1 --> P2
        P2 -. on demand .-> Comparator((comparator))
        Comparator --> Comparison[comparison.md]
        Comparison -.-> P2
    end

    PlanResume --> P2
    Plan --> Sketch[sketch design.md sections<br/>to user]
    Sketch --> Confirm{user confirms<br/>Plan to Build}
    Confirm -->|no| Plan
    Confirm -->|yes| BuildImpl

    subgraph BuildImpl["Build-implement"]
        direction TB
        WriteDesign[write design.md] --> Members{member count}
        Members -->|>= 2 papers| Surgery((coder Stage 2<br/>component surgery))
        Members -->|exactly 1| Extension((coder Stage 2<br/>extension regime))
        Surgery --> ScaffoldCode[scaffold.py +<br/>methods/slug/extracted.py]
        Extension --> ExtCode[methods/slug/extended.py +<br/>synth/ + run.py]
        ScaffoldCode --> CritGate
        ExtCode --> CritGate
        CritGate{critic fidelity gate<br/>extraction or extension}
        CritGate -->|FAIL| FixCode[experimenter routes<br/>fixes back to coder]
        FixCode --> Surgery
        FixCode --> Extension
        CritGate -->|PASS| Smoke((coder re-invoked<br/>--smoke))
        Smoke --> SmokeGate{smoke gate<br/>run.py --smoke}
        SmokeGate -->|FAIL or TIMEOUT| FixCode
        SmokeGate -->|PASS| HandBack[hand back to user<br/>run full experiment]
    end

    HandBack --> UserRun([user runs full experiment<br/>results land in run/results/])
    UserRun --> BuildEval

    subgraph BuildEval["Build-evaluate"]
        direction TB
        Eval((evaluator)) --> Findings[findings.md]
    end

    Findings --> Judge([user judges design as a whole])

    SpecLearn[/spec.md + code_map.md<br/>from Learning suite/] -. feeds .-> Plan
    VaultMethod[/vault method.py<br/>Stage 1 output/] -. inherited by .-> Extension
    VaultMethod -. extracted from .-> Surgery
```

`experimenter`, `comparator`, `coder`, `evaluator`. The `experimenter`
orchestrates an interactive design session (writing `design.md`,
including the **harness interface** every method conforms to), invoking
the `comparator` for conceptual method trade-offs (`comparison.md`). The
`coder`'s **Stage 2 adapt-mode** then wraps each paper's Stage-1 method
(the reusable `Method` already in `<vault>/<slug>/code/`) to that harness
under `sandbox/experiments/<topic>/methods/`, and the `evaluator`
interprets the runs into `findings.md`.

**The two suites connect at the method code:** Stage 1 (Learning suite)
writes the paper-bound method once in the vault; Stage 2 (Experimenter
suite) wraps it to a topic harness. This mirrors PaperLab's firewall
philosophy — paper-bound knowledge lives with the paper, experiment glue
lives with the experiment — and rides the two-hop fidelity bridge: hop-1
(math → blueprint) guarded by the critic, hop-2 (blueprint → code)
guarded by invariants-as-assertions in Stage 1.

**Status:** the Learning suite is shipped, now including the `coder`'s
Stage 1 (`/coder code <slug>`, shipped 2026-06-04). In the Experimenter
suite the `comparator` and the `experimenter` design-phase shell are
shipped; the `coder`'s Stage 2 adapt-mode and the `evaluator` are
designed (see `ROADMAP.md`).

## Memory sharing design

PaperLab agents do **not** message each other directly. They share state
through files on disk — the vault is the shared memory substrate, the
repo holds source material and per-topic sandbox state, and a per-paper
citation cache survives across sessions. Every artifact has **exactly
one writer agent** (the firewall principle), and any number of reader
agents. Backend invocations (`tutor` → `explainer`, `experimenter` →
`coder` / `evaluator`, `implementer` → `critic` blueprint-check, ...)
still hand control off via these files: the parent writes a draft or
reads the child's output, no in-memory IPC.

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 40, 'rankSpacing': 70, 'padding': 12}, 'themeVariables': {'fontSize': '18px'}}}%%
flowchart LR
    subgraph Agents["Agents"]
        direction TB
        Acq((acquirer))
        Dis((dissector))
        Imp((implementer))
        Cod((coder))
        Cri((critic))
        Tut((tutor))
        Exp((explainer))
        Cmp((comparator))
        Exr((experimenter))
        Evl((evaluator))
    end

    subgraph Paper["Per-paper vault: &lt;slug&gt;/"]
        direction TB
        PI[paper-info.md]
        SP[spec.md]
        CB[code_blueprint.md]
        VC[code/method.py + test_invariants.py]
        CM[code_map.md]
        CR[critic_reviews.md / code_review.md]
        TL[tutor_log.md]
        EC[concept-slug.md / synth-slug.md]
        TC[concept.md / synth.md / tutor_notes.md]
    end

    subgraph Topic["Per-topic vault: experiments/&lt;topic&gt;/"]
        direction TB
        CO[comparison.md]
        DE[design.md]
        FI[findings.md]
    end

    subgraph Side["Repo-side state"]
        direction TB
        CC[papers/&lt;slug&gt;/.cache/citations/]
        SB[sandbox/experiments/&lt;topic&gt;/<br/>scaffold.py + methods/ + run/results/]
    end

    Acq ==> PI
    Dis ==> SP
    Imp ==> CB
    Imp ==> CM
    Cod ==> VC
    Cod ==> SB
    Cri ==> CR
    Tut ==> TL
    Tut ==> TC
    Exp ==> EC
    Cmp ==> CO
    Exr ==> DE
    Evl ==> FI

    SP -.-> Imp
    SP -.-> Cri
    SP -.-> Tut
    SP -.-> Exp
    SP -.-> Cmp
    SP -.-> Exr
    SP -.-> Evl
    CB -.-> Cod
    CB -.-> Cri
    VC -.-> Imp
    VC -.-> Cri
    VC -.-> Cod
    CM -.-> Cri
    CM -.-> Tut
    CM -.-> Cmp
    CM -.-> Cod
    CR -.-> Tut
    TL -.-> Tut
    EC -.-> Tut
    CO -.-> Exr
    DE -.-> Cod
    DE -.-> Evl
    SB -.-> Evl
    SB -.-> Cri
```

**Reading the diagram.** Thick green arrows are *writes* (one writer per
artifact); thin dashed arrows are *reads* (any agent that needs the
artifact). The single-writer rule is what makes the firewall checks
(blueprint-check, hop-2-vs-spec, extraction-fidelity, extension-fidelity)
auditable: the `critic` only ever reads what another agent wrote, never
something it produced itself.

**Three kinds of shared memory.**

1. **Per-paper artifacts** under `<vault>/<slug>/` are the canonical
   substrate. `spec.md` is read by almost every downstream agent — it is
   the de-facto interchange format. `code_map.md` and the critic's
   audits propagate the same way.
2. **Per-topic artifacts** under `<vault>/experiments/<topic>/`
   (`comparison.md`, `design.md`, `findings.md`) carry multi-paper
   experiment state and are read only by Experimenter-suite agents and
   the user.
3. **Repo-side state.** `papers/<slug>/.cache/citations/` is the
   citation-verifier's resolver cache (survives a session, cleared
   manually). `sandbox/experiments/<topic>/` holds the runnable scaffold,
   per-method extracted/extended code, and the JSON run results — the
   hand-off surface between the `coder`'s output, the user's compute
   run, and the `evaluator`'s read.

**Two cross-cutting memory channels.**

- **Tutor self-memory.** `tutor_log.md` is the only file an agent both
  reads and writes for itself: the `tutor` appends per-turn breadcrumbs
  every turn and reads them back on `/tutor` resume. Persistent memory
  across sessions, no other agent touches it.
- **Cross-suite bridge.** Two artifacts move information between the
  Learning and Experimenter suites: `spec.md` (read by `comparator`,
  `experimenter`, `evaluator`) and `code/method.py` (inherited by the
  `coder`'s Stage-2 extension regime, extracted-from by component
  surgery). Everything else stays inside its suite.

**What is *not* shared.** No agent has access to another agent's
prompt, scratchpad, conversation history, or in-flight reasoning. If
information needs to flow between agents, it has to be written to one
of the artifacts above. This is what keeps the firewalled critic gates
honest and what makes a regenerated `spec.md` automatically propagate
to every reader the next time they run.
