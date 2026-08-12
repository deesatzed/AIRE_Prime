import json

from aire_prime.experiments.e3.report import blocks_for_analysis, write_e3_result
from aire_prime.experiments.e3.run import run_e3_evaluation


def test_result_manifest_and_report_are_closed_and_grounding_bounded(tmp_path) -> None:
    result = run_e3_evaluation(split="development", root_seed=301)
    report = write_e3_result(result, tmp_path / "e3", analyze=True)

    assert report.grounding == "G-S"
    assert report.classification in {"partial", "negative", "undetermined"}
    assert len(blocks_for_analysis(result)) == 6 * 8
    manifest = json.loads((tmp_path / "e3" / "e3_manifest.json").read_bytes())
    assert manifest["required_artifacts"] == [
        "e3_manifest.json",
        "e3_result.json",
        "e3_report.json",
    ]


def test_missing_resource_block_is_retained_as_undetermined(tmp_path) -> None:
    result = run_e3_evaluation(split="development", root_seed=301)
    broken_block = result.blocks[0].model_copy(update={"resource_state": "undetermined"})
    broken = result.model_copy(update={"blocks": (broken_block, *result.blocks[1:])})
    report = write_e3_result(broken, tmp_path / "e3", analyze=True)
    assert report.classification == "undetermined"
