# Handoff

> Update this file at the end of every PR. Treat it as the “what changed last” file.

## Last completed change

This PR adds a large AI-first documentation system under `docs/AI_FACTORY/`, updates root discoverability, and adds `.github/copilot-instructions.md` so future agents can resume work with minimal prompting.

## Verified in this session

```bash
pip install -e ".[dev]"
pytest
python tools/validate-assets.py assets/examples/ --verbose
audio-engine list-styles
audio-engine generate-sfx --prompt "ui confirm click" --duration 0.15 --output /tmp/audio_factory_ui.wav
audio-engine qa --input /tmp/audio_factory_ui.wav
audio-engine generate-game-assets --output-dir /tmp/audio_factory_assets --only sfx --force --quiet
```

Observed result:

- `314 passed`
- asset-manifest examples validated successfully
- CLI style listing worked
- one-off SFX generation worked
- SFX-only batch generation produced 31 effects

## Immediate next best task

Create a committed example project audio plan and generation request set for a `GameRewritten`-style game slice, including seeds, intended output paths, and review status fields.

## Files future agents should read first

1. `docs/AI_FACTORY/README.md`
2. `docs/AI_FACTORY/CURRENT_STATE.md`
3. `docs/AI_FACTORY/ACTIVE_WORK.md`
4. `docs/AI_FACTORY/PLAYBOOKS/AGENT_WORKFLOW.md`
5. relevant subsystem/style/schema docs

## Handoff checklist

- [x] Mission and non-goals documented
- [x] Current state documented
- [x] Roadmap documented
- [x] Agent workflow documented
- [x] Troubleshooting documented
- [x] Style-family safety guidance documented
- [x] Integration direction for `GameRewritten` documented
- [ ] Project-level audio plan example implemented in repo
- [ ] Batch generation request format implemented in code
- [ ] Audio QA/review automation added
