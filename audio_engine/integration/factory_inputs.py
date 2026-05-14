from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class FactoryInputError(ValueError):
    """Raised when a factory input artifact does not match the expected shape."""


@dataclass(frozen=True)
class AudioPlanPriorities:
    music: str
    sfx: str
    voice: str


@dataclass(frozen=True)
class AudioPlanTarget:
    asset_id: str
    gameplay_role: str
    target_path: str
    loop: bool
    duration_target_seconds: float
    mood: list[str] = field(default_factory=list)
    review_priority: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AudioPlanAssetGroup:
    group_id: str
    type: str
    required: bool
    targets: list[AudioPlanTarget]


@dataclass(frozen=True)
class AudioPlan:
    plan_version: str
    project: str
    scope: str
    priorities: AudioPlanPriorities
    style_families: list[str]
    asset_groups: list[AudioPlanAssetGroup]
    coverage_goal: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GenerationRequestOutput:
    target_path: str
    format: str
    sample_rate: int
    channels: int


@dataclass(frozen=True)
class GenerationRequestQA:
    loop_required: bool
    review_status: str
    notes: list[str] = field(default_factory=list)
    acceptance_profile: str | None = None
    loudness_target: str | None = None


@dataclass(frozen=True)
class GenerationRequest:
    request_version: str
    request_id: str
    asset_id: str
    type: str
    backend: str
    seed: int
    prompt: str
    style_family: str
    output: GenerationRequestOutput
    qa: GenerationRequestQA
    replace_existing: bool | None = None
    supersedes_request_id: str | None = None


@dataclass(frozen=True)
class GenerationRequestBatch:
    request_batch_version: str
    project: str
    scope: str
    requests: list[GenerationRequest]


def load_audio_plan(path: str | Path) -> AudioPlan:
    source_path = Path(path)
    data = _load_json_document(source_path)
    return parse_audio_plan(data, source=str(source_path))


def load_generation_request_batch(path: str | Path) -> GenerationRequestBatch:
    source_path = Path(path)
    data = _load_json_document(source_path)
    return parse_generation_request_batch(data, source=str(source_path))


def parse_audio_plan(data: Any, *, source: str = "<memory>") -> AudioPlan:
    root = _require_mapping(data, source)
    priorities_data = _require_mapping(root.get("priorities"), f"{source}.priorities")
    asset_groups_data = _require_list(root.get("assetGroups"), "assetGroups", source)

    priorities = AudioPlanPriorities(
        music=_require_str(priorities_data.get("music"), "music", f"{source}.priorities"),
        sfx=_require_str(priorities_data.get("sfx"), "sfx", f"{source}.priorities"),
        voice=_require_str(priorities_data.get("voice"), "voice", f"{source}.priorities"),
    )

    asset_groups = [
        _parse_audio_plan_asset_group(group, index=index, source=source)
        for index, group in enumerate(asset_groups_data)
    ]

    return AudioPlan(
        plan_version=_require_str(root.get("planVersion"), "planVersion", source),
        project=_require_str(root.get("project"), "project", source),
        scope=_require_str(root.get("scope"), "scope", source),
        priorities=priorities,
        style_families=_require_str_list(root.get("styleFamilies"), "styleFamilies", source),
        asset_groups=asset_groups,
        coverage_goal=_optional_str(root.get("coverageGoal"), "coverageGoal", source),
        notes=_optional_str_list(root.get("notes"), "notes", source),
    )


def parse_generation_request_batch(data: Any, *, source: str = "<memory>") -> GenerationRequestBatch:
    root = _require_mapping(data, source)
    requests_data = _require_list(root.get("requests"), "requests", source)

    requests = [
        _parse_generation_request(request, index=index, source=source)
        for index, request in enumerate(requests_data)
    ]

    return GenerationRequestBatch(
        request_batch_version=_require_str(root.get("requestBatchVersion"), "requestBatchVersion", source),
        project=_require_str(root.get("project"), "project", source),
        scope=_require_str(root.get("scope"), "scope", source),
        requests=requests,
    )


def _load_json_document(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FactoryInputError(f"Factory input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FactoryInputError(f"Invalid JSON in factory input file {path}: {exc}") from exc


def _parse_audio_plan_asset_group(data: Any, *, index: int, source: str) -> AudioPlanAssetGroup:
    context = f"{source}.assetGroups[{index}]"
    mapping = _require_mapping(data, context)
    targets_data = _require_list(mapping.get("targets"), "targets", context)
    targets = [
        _parse_audio_plan_target(target, index=target_index, source=context)
        for target_index, target in enumerate(targets_data)
    ]
    return AudioPlanAssetGroup(
        group_id=_require_str(mapping.get("groupId"), "groupId", context),
        type=_require_str(mapping.get("type"), "type", context),
        required=_require_bool(mapping.get("required"), "required", context),
        targets=targets,
    )


def _parse_audio_plan_target(data: Any, *, index: int, source: str) -> AudioPlanTarget:
    context = f"{source}.targets[{index}]"
    mapping = _require_mapping(data, context)
    return AudioPlanTarget(
        asset_id=_require_str(mapping.get("assetId"), "assetId", context),
        gameplay_role=_require_str(mapping.get("gameplayRole"), "gameplayRole", context),
        target_path=_require_str(mapping.get("targetPath"), "targetPath", context),
        loop=_require_bool(mapping.get("loop"), "loop", context),
        duration_target_seconds=_require_number(mapping.get("durationTargetSeconds"), "durationTargetSeconds", context),
        mood=_optional_str_list(mapping.get("mood"), "mood", context),
        review_priority=_optional_str(mapping.get("reviewPriority"), "reviewPriority", context),
        notes=_optional_str_list(mapping.get("notes"), "notes", context),
    )


def _parse_generation_request(data: Any, *, index: int, source: str) -> GenerationRequest:
    context = f"{source}.requests[{index}]"
    mapping = _require_mapping(data, context)
    output_data = _require_mapping(mapping.get("output"), f"{context}.output")
    qa_data = _require_mapping(mapping.get("qa"), f"{context}.qa")

    return GenerationRequest(
        request_version=_require_str(mapping.get("requestVersion"), "requestVersion", context),
        request_id=_require_str(mapping.get("requestId"), "requestId", context),
        asset_id=_require_str(mapping.get("assetId"), "assetId", context),
        type=_require_str(mapping.get("type"), "type", context),
        backend=_require_str(mapping.get("backend"), "backend", context),
        seed=_require_int(mapping.get("seed"), "seed", context),
        prompt=_require_str(mapping.get("prompt"), "prompt", context),
        style_family=_require_str(mapping.get("styleFamily"), "styleFamily", context),
        output=GenerationRequestOutput(
            target_path=_require_str(output_data.get("targetPath"), "targetPath", f"{context}.output"),
            format=_require_str(output_data.get("format"), "format", f"{context}.output"),
            sample_rate=_require_int(output_data.get("sampleRate"), "sampleRate", f"{context}.output"),
            channels=_require_int(output_data.get("channels"), "channels", f"{context}.output"),
        ),
        qa=GenerationRequestQA(
            loop_required=_require_bool(qa_data.get("loopRequired"), "loopRequired", f"{context}.qa"),
            review_status=_require_str(qa_data.get("reviewStatus"), "reviewStatus", f"{context}.qa"),
            notes=_optional_str_list(qa_data.get("notes"), "notes", f"{context}.qa"),
            acceptance_profile=_optional_str(qa_data.get("acceptanceProfile"), "acceptanceProfile", f"{context}.qa"),
            loudness_target=_optional_str(qa_data.get("loudnessTarget"), "loudnessTarget", f"{context}.qa"),
        ),
        replace_existing=_optional_bool(mapping.get("replaceExisting"), "replaceExisting", context),
        supersedes_request_id=_optional_str(mapping.get("supersedesRequestId"), "supersedesRequestId", context),
    )


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FactoryInputError(f"{context} must be an object")
    return value


def _require_list(value: Any, field_name: str, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise FactoryInputError(f"{context}.{field_name} must be a list")
    return value


def _require_str(value: Any, field_name: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FactoryInputError(f"{context}.{field_name} must be a non-empty string")
    return value


def _optional_str(value: Any, field_name: str, context: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field_name, context)


def _require_bool(value: Any, field_name: str, context: str) -> bool:
    if not isinstance(value, bool):
        raise FactoryInputError(f"{context}.{field_name} must be a boolean")
    return value


def _optional_bool(value: Any, field_name: str, context: str) -> bool | None:
    if value is None:
        return None
    return _require_bool(value, field_name, context)


def _require_int(value: Any, field_name: str, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FactoryInputError(f"{context}.{field_name} must be an integer")
    return value


def _require_number(value: Any, field_name: str, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FactoryInputError(f"{context}.{field_name} must be a number")
    return float(value)


def _require_str_list(value: Any, field_name: str, context: str) -> list[str]:
    items = _require_list(value, field_name, context)
    return [_require_str(item, f"{field_name}[{index}]", context) for index, item in enumerate(items)]


def _optional_str_list(value: Any, field_name: str, context: str) -> list[str]:
    if value is None:
        return []
    return _require_str_list(value, field_name, context)
