# Codebook: NEEDS (which literatures hold results a sub-question uses)

## Task

Your batch file holds sub-questions (each with an ID and the question of the research agenda it refines: Rules, Detection, Repair, Change or Neutrality) and literatures shown under neutral codes L01 to L11. Each literature is given as its list of seed papers (OpenAlex ID, title, year and abstract, or "no abstract in OpenAlex"), in random order.

For every pair of a sub-question q and a literature L, decide NEEDS(q, L): yes or no.

NEEDS(q, L) is yes if and only if at least one seed of L, judged from its title and abstract, holds a result that an answer to q would use. A result is a theorem, impossibility, characterisation or bound; a mechanism, protocol, algorithm or estimator with a stated property; an identification or testability condition; an empirical finding; or a legal doctrine, liability rule or institutional analysis with a stated conclusion. "Would use" means the result could serve an answer to q as a premise, a tool, a bound the answer must respect, a construction to adapt, or a partial answer in a narrower setting (for example, one designer instead of several owners). It is no if the seeds share only vocabulary or topic with q, only motivate q, or hold results that q would not use.

Judge each seed by what its title and abstract state. Where the batch shows "no abstract in OpenAlex" (books, older papers), you may use the seed's main result only if you can state that result in one sentence, and you must record the basis as "knowledge". Do not credit a literature for results in later papers that cite its seeds, and do not reason from a literature's field or reputation: the literatures are shown under neutral codes.

## Examples (not in the coded set)

The examples use a practice sub-question and papers that are not seeds, so that no coded cell is shown.

Practice sub-question E: "When agents of different owners are matched to tasks offered by other owners, which matching rules leave no pair of an agent and a task that would both prefer each other to their assignment, and can an owner gain by misreporting its agent's preferences?"

Yes: a literature whose seeds include Gale and Shapley 1962, "College admissions and the stability of marriage" (abstract: a stable assignment always exists and the deferred-acceptance procedure finds it). The result is an existence theorem and a construction that answer E in the one-designer case; E would use it. Record the seed ID, the result in one sentence and basis "abstract".

Yes: a literature whose seeds include Roth 1982, "The economics of matching: stability and incentives" (no stable matching rule makes truthful reporting dominant for both sides). E's second clause must respect this bound. Basis "abstract" or "knowledge".

No: a literature whose seeds include Dijkstra 1959, "A note on two problems in connexion with graphs" (shortest paths). The topic, assignment over a graph, is near, but no stated result is one that E would use.

No: a literature whose seeds argue that matching markets for AI services should be studied, without stating a result. Motivation alone is not a result.

## Output format

JSON Lines, one object per (sub-question, literature) pair, every pair exactly once (25 sub-questions x 11 literatures = 275 lines), with the literature's code as shown in your batch:

{"q": "R1", "lit": "L07", "need": "yes", "seeds": ["W2029050771"], "result": "one sentence naming the result used", "basis": "abstract"}

{"q": "R1", "lit": "L08", "need": "no", "seeds": [], "result": "", "basis": ""}

Rules (checked when the file is loaded): need is "yes" or "no"; a yes carries one to three seed IDs, each in that literature's seed list in your batch, a non-empty result and a basis in {abstract, title, knowledge}; a no carries an empty seed list.
