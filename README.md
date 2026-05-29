# paperlab

`paperlab` is a multiagent system to help students to understand papers in machine learning and deep learning.

## Work flow


```mermaid
flowchart LR
    Acquirer((acquirer)) --> Sources[PDF / Git repo]
    Sources --> Dissector((dissector))
    Dissector --> Spec[spec.md]

    Spec --> Implementer((implementer))
    Sources --> Implementer
    Implementer --> CodeMap[code_map.md]
    Implementer --> DeepDive[code_map__slug__component.md]

    Spec --> Critic((critic))
    CodeMap --> Critic
    Critic --> Review[critic_reviews.md]

    Spec --> Tutor((tutor))
    Tutor -. invokes .-> Explainer((explainer))
    Explainer --> ConceptBound[concept-slug.md]
    Tutor --> Concept[concept.md]
    Tutor --> Synth[synth__a__b.md]
    Tutor --> TutorLog[tutor_log.md / tutor_notes.md]
```

The user-facing concept interface is the `tutor` (`/tutor <slug>`); it
invokes the `explainer` in the background. The **experimenter suite**
(multi-paper empirical comparison) runs alongside this per-paper flow:
the `comparator` (shipped) compares methods across papers along an axis
and writes `comparison.md` to `<vault>/experiments/<topic>/`; the
`experimenter`, `coder`, and `evaluator` are designed (see `ROADMAP.md`).
