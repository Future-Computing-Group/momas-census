# Codebook LLM-BASIS (v2)

Added 2026-11-06. It defines the population "agents built on large language models" by coding, replacing the LLM-agent keyword screen as the definition (the screen stays as a sampling stratum). Coded for every 2025 paper whose primary code is AGENT=yes.

v2 (2026-11-06, after a two-coder pilot of 20 papers with full agreement): the clarifications below record the pilot's edge cases; no pilot code changes.

Code each paper from its title and abstract only, reading the abstract to its end.

LLM_BASIS: yes if the decision-makers the paper studies are large language models, or are driven by one (an LLM, a vision-language model or a multimodal foundation model chooses the actions, possibly through tools, code or a scaffold); no if the agents are of another kind (reinforcement-learning policies not built on a language model, bandit learners, classical planners, robots with conventional controllers, game-theoretic players, human participants), including papers that use an LLM only as a tool, a reward model, a data generator or an evaluator for agents that are not themselves LLMs; na if the abstract does not say what the agents are built on.

Words such as "agentic", "web agent", "GUI agent" or "coding agent" are not enough by themselves: code yes only when the abstract says or plainly implies (for example by naming GPT, Claude, Llama or Qwen as the agent) that a language model drives the agent.

Edge cases: "reasoning models" or "AI agents" built on them count as yes; an agent the title or abstract calls LLM-, VLM- or MLLM-based counts as yes even when an LLM also serves as its reward model or data generator; in-context RL agents, transformers trained from scratch on control tasks, and diffusion or other non-language foundation models are no unless a language model drives them; an embodied agent that only receives language instructions, with no statement that a language model chooses its actions, is na.

last_words: copy the abstract's final five whitespace-separated tokens as they appear, LaTeX and special characters included.

Output one JSON object per paper: {"id", "llm_basis" (yes/no/na), "confidence" (high/medium/low), "note" (one short sentence quoting the phrase that decided it), "last_words" (the last five words of the abstract exactly as read)}.
