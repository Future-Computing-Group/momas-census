# Codebook: who the other parties are (decomposition of the census cell, v1)

Purpose: the census cell "several principals with several owners" (POLICY_SETTERS and PRINCIPALS several, no outside attacker; codebook-policy-v2.2.md, and earlier the v3.4 OWNERS and INTERESTS codes of codebook-v3.md) admits papers whose other parties are humans or modelled firms as well as papers with AI agents of different owners. This one-question re-code splits the confirmed cell papers by the kind of decision-maker on the several sides, so that the share with AI agents of separately owned parties can be reported beside the headline share.

Code each paper from its title and abstract only, reading the abstract to its end, without venue or year. Code the setting the method or analysis is meant for, as in codebook-v3.md, not only the paper's experiments.

PARTIES: what the decision-makers on the several sides of the setting are.
- ai-agents: on at least two sides there are artificial agents (learning agents, language-model agents, bots, algorithms that choose actions over several steps) that act for parties who own them separately, e.g. pricing algorithms of competing firms, autonomous agents of different users or organizations, bidding agents for different advertisers, multi-agent reinforcement learners with their own rewards meant for deployment by different parties.
- humans: the other parties are humans acting for themselves (users, applicants, voters, workers, human bidders or players, crowd participants), facing an AI system or a mechanism; one side may be an AI system, but the parties on the other sides are people.
- formal-model: the parties are abstract players, firms, bidders, buyers and sellers or agents in a game-theoretic, economic or learning-in-games model, with no statement that artificial agents act for them (an equilibrium or mechanism analysis, or no-regret dynamics among abstract players).
- other: anything else, including federated or cross-silo clients that share one goal, mixed cases that fit none of the above, and abstracts that do not say.

When the abstract states that the players are learning algorithms or AI agents deployed by different parties, code ai-agents even inside a formal model. When it studies learning dynamics among abstract players without saying who deploys them, code formal-model.

Output one JSON object per paper: {"id", "parties" (ai-agents / humans / formal-model / other), "confidence" (high / medium / low), "quote" (the shortest verbatim phrase from the abstract that decided PARTIES, or an empty string)}.
