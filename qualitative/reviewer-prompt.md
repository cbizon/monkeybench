# Monkeybench qualitative reviewer

Review one completed Monkeybench trial using only the supplied evidence.

Read `contract/RUBRIC.md` before beginning. The deterministic evaluator is
authoritative for localization counts, typing accuracy, and the confusion
matrix. Do not visually re-grade cells or silently recalculate those results.

Follow this order:

1. Characterize the observable transcript: how the agent used the training
   material, inspected images, chose locations, assigned cell types, used tools
   or scripts, handled failures, and finalized its submission.
2. Characterize localization performance from total and per-image true
   positives, false positives, and false negatives.
3. Characterize typing performance from the reported accuracy and confusion
   matrix. Identify important off-diagonal confusions and describe the row and
   column marginals, including class imbalance.
4. State a concise overall bottom line, strengths, weaknesses, and review
   limitations.

Requirements:

- Inspect the supplied copies only and do not modify candidate evidence.
- Treat deterministic metrics as facts unless the supplied files directly
  contradict one another.
- Do not infer unobserved reasoning or expose private chain-of-thought.
- Distinguish direct transcript observations from interpretation.
- Ignore candidate provider and model identity when judging performance.
- Cite evidence for transcript, localization, and typing characterizations.
- Name the training files or media the transcript shows the agent actually
  consulting. Distinguish reading training metadata from visually inspecting
  guides or watching the supplied video. Say explicitly when evidence of use
  is absent.
- Describe concrete difficulties, failed tool calls, validation problems, or
  uncertainty visible in the transcript and what the agent did in response.
- Write the overall bottom line as a plain-language synthesis rather than a
  list of metrics. First state roughly what fraction of real cells were found,
  compare false positives with true positives, and then characterize how
  accurately the localized cells were typed.
- Name the important type confusions. When errors concentrate in rarer cell
  types, say which rare types were assigned to which common types rather than
  referring vaguely to "leukocytes."
- If deterministic evaluation failed, characterize the transcript and mark
  unavailable performance sections accordingly.
- Do not produce a composite qualitative or numerical score.

Return only JSON conforming to `resolved-output.schema.json`.
