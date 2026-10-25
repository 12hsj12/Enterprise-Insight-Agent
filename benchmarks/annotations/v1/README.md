# Quality Annotations v1

These files are the final, human-approved quality annotations for the Enterprise Insight Agent benchmark.

- **Rubric:** `QUALITY_ANNOTATION_RUBRIC_V1`
- **Method:** human-reviewed, AI-assisted claim segmentation and saved-evidence matching under the frozen calibration protocol
- **Information cutoff:** 2026-09-05
- **Coverage:** 24 completed reports across development and holdout splits
- **Golden calibration:** EI_001_A was reproduced and reviewed at item level before bulk annotation
- **Human review gate:** all flagged source-resolution items and extreme-metric cases were explicitly reviewed and approved before this version was created
- **EI_010_A caveat:** it has zero explicit body Markdown citation links, so Citation Correctness is `null`, not zero; APA-style author–year references are not counted by the frozen protocol
- **Verification boundary:** only saved benchmark evidence was used; no live-web verification or live benchmark rerun was performed
- **Raw artifact integrity:** raw benchmark reports and result artifacts were not edited

The four `annotations_{variant}_{split}_final.json` files are the scoring-ready subsets. Each contains only run IDs belonging to its corresponding raw benchmark `results.json`. The two broader development and holdout files provide convenient split-level archival views.
