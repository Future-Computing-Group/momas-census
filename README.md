# Multi-owner multi-agent systems: census code and data

Data, codebooks and code for the census of accepted papers and the coded sample of agent deployments in the Perspective "Multi-owner multi-agent systems: from better agents to the rules between them" (Lauri Lovén, University of Oulu).

## What this repository regenerates

From the committed coded labels and stored query results, the repository regenerates, with no network access and no model calls:

- every number of the Supplementary Information and of the main text that is not a cited fact or a design constant: the LaTeX fragments in `si/` (the manuscript inputs them as `\input{si/NAME.tex}`, so no number is typed by hand);
- the fragments that only `docs/census-methods.md` cites, in `docs/fragments/`;
- Fig. 2 (`fig/census-fieldmap.pdf` and `.png`).

The coding itself (first-stage open-weight model runs on a GPU cluster, second-stage Claude coders) and the web fetches are documented and scripted here but are not rerun by the check below.

## Clean-clone check

```
pip install -r requirements.txt     # Python 3.11; matplotlib and numpy pinned for a byte-identical Fig. 2
sh test_clean_clone.sh              # or: python3 -m pytest test_clean_clone.py
```

`test_clean_clone.sh` clones the committed HEAD into a temporary directory, checks every input against `data/inputs-sha256.txt` (`shasum -a 256 -c`), runs `si_tables.py`, `attention.py` and `fig_census_fieldmap.py` there, and requires `diff -r` of the regenerated `si/` and `docs/fragments/` against the committed ones to be empty, the estimate side files and both figure files to be byte-identical, and the clone's working tree to stay clean. The full test suite runs with `python3 -m pytest` (serially; tests that need the local, unreleased files skip). `test_typed_numerals.py` checks the manuscript when `NMI_MANUSCRIPT` points to its folder.

## Pipeline

In order, as in Supplementary Note 4 (each script's docstring gives its inputs, outputs and options):

1. Frames. `fetch_frames.py` fetches the paper lists into `data/raw/` and checks them against `data/raw-manifest.json`; `--delineation` writes `data/frames-delineation.json`. `census.py`, `build_sample.py`, `add_ec_record.py` (adds the one EC 2025 research paper that OpenAlex types as paratext) and `make_batches.py` drew and batched the stratified sample of the earlier coding stage (codebook version 2, `codebook.md`).
2. First-stage inputs and coding. `xfam_inputs.py` builds the items `data/xfam/items-{full,ext,ext-ea}.jsonl` and the model calls (codebook version 3.4, `codebook-v3.md`; policy codebook `codebook-policy-v2.2.md`); `roihu/xfam.sbatch`, `roihu/xfam_client.py` and `roihu/pull.sh` ran the open-weight model (provenance in `data/xfam/PROVENANCE.md`); parsed codes are in `data/xfam/*/results-parsed.jsonl`.
3. Confirmation draws. `xfam_full.py` draws stage 2 and writes the blind batches in `data/batches/`; `draw_stage2_parts.py` draws the later parts (reproduced byte for byte by test). The second-stage codes are in `data/coded/`, the briefs that produced them in `coding/`. `pilot_agreement.py` computes the pilot agreement of the policy codebook from `data/pilot/`.
4. Deployments. `fetch_deploy_pages.py` snapshots the vendor case pages (`data/deploy-items.json`, hashes in `data/deploy-pages-manifest.json`); `deploy.py` and `deploy_layers.py` (codebook `codebook-deploy-layers.md`) estimate the deployment shares.
5. Estimates. `estimate.py`, `twostage.py`, `round2.py`, `tipping.py`, `reanalyses.py`, `deploy_layers.py`, `attention.py`, `bibliometric.py` and, under `fields/run4-broad/`, `analyse.py` and `layers.py` write the `data/estimates-*.json`, `data/bibliometric*.json` and `data/fields/` files.
6. Fragments and figure. `python3 si_tables.py [si dir] [docs dir] [counts file]` (with `si_ext.py` and `fields/run4-broad/crossmap.py`) and `python3 attention.py [si dir] [estimates file]` write the fragments; `python3 fig_census_fieldmap.py data/fields fig/census-fieldmap` draws Fig. 2.

`fields/README.md` documents the citation-link runs behind Fig. 2b and Supplementary Note 3, and `docs/census-methods.md` the analyses that the Supplementary Information does not report.

## Data and provenance

- Conference papers. NeurIPS and ICML 2020 and 2025 and ICLR 2025: the conferences' public lists of accepted papers (`https://{neurips,icml,iclr}.cc/static/virtual/data/{conference}-{year}-orals-posters.json`), retrieved 2026-11-06 and 2026-11-07. ACM EC 2025: the OpenAlex works API (source S4363608973, publication year 2025). AAMAS 2025: the IFAAMAS proceedings contents (`https://www.ifaamas.org/Proceedings/aamas2025/`) with the publisher's Crossref abstracts (DOI prefix 10.65109). The raw lists are not released, since they carry author records (institutions, biographies, some e-mail addresses); their sha256 is in `data/raw-manifest.json` and `fetch_frames.py` refetches and checks them (the live lists change after a conference). Released instead: the titles and abstracts the coders saw (`data/xfam/items-*.jsonl`, `data/stage2-items.json`, `data/batches/`) and, for the frame table, each record's title, OpenReview group and OpenAlex type (`data/frames-delineation.json`). One AAMAS abstract printed its first author's e-mail address; the released files carry `[e-mail address removed]` in its place, so `items-ext.jsonl` no longer matches the sha256 recorded for the coder inputs in `data/xfam/ext-sha256.txt` and `policy-sha256.txt`, which pin the files as dispatched.
- OpenAlex. The bibliometric counts (`bibliometric.py`, `data/bibliometric*.json`), the citation-link corpora (`fields/`, results in `data/fields/`) and the citation counts (`fields/run5-attention/`, `data/attention/`) come from `https://api.openalex.org`, retrieved 2026-11-09 and 2026-11-10. The raw responses are not in the repository (about 140 MB of archives, not needed to regenerate any released number); `data/raw-archives-sha256.txt` pins the archives and `fields/README.md` describes them.
- Vendor case pages. `data/deploy-items.json` lists the URL, vendor and organization of each of the deployment pages; `data/deploy-pages-manifest.json` holds the fetch time and the sha256 of each page's HTML and extracted text. The pages are third-party content and are not released; no released number needs their text, since the coded labels in `data/coded/` carry the deciding quotes.
- Inputs of the check. `data/inputs-sha256.txt` pins every file that the fragment and figure scripts read; `test_inputs_manifest.py` checks it.
- Codebooks. The changelog and purpose lines of the codebooks were edited for release; their coding rules, definitions and worked examples are as dispatched to the coders. The sha256 values pinned in the code and in `data/` (`xfam_inputs.py`, `data/xfam/policy2-sha256.txt`, `data/pilot/`, `test_deploy_layers.py`) are those of the files as released. The pilot's rule-implied codes in `data/pilot/` label the rules by their codebook v2.2 names (R5 to R10).
- Second-coder draw of the parties batch. The second coder's 80 of the 391 cell papers of the first parties coding (`data/coded/r2-parties-dup.jsonl`) cannot be reproduced by any seeded procedure in this repository; the stored batch and coded files are the record of that draw.

## Licence

Code: MIT (`LICENSE`). Data, coded labels, codebooks and documentation (everything under `data/`, `coding/`, `docs/`, `si/`, `fig/` and the `codebook*.md` files): Creative Commons Attribution 4.0 International (CC BY 4.0, `LICENSE-data`). Paper titles and abstracts remain their authors' and publishers' and are included for research use as published metadata. To cite, see `CITATION.cff`.
