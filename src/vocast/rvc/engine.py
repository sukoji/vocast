from __future__ import annotations

from pathlib import Path

from vocast.rvc.registry import inference_defaults, resolve_model


class RvcEngine:
    def __init__(self, model_name: str, *, device: str = "cuda:0", **param_overrides):
        try:
            from rvc_python.infer import RVCInference
        except ImportError as e:
            raise ImportError(
                "rvc-python not installed. pip install -r requirements.txt"
            ) from e

        pth, index, version = resolve_model(model_name)
        self.model_name = model_name
        self.params = {**inference_defaults(), **param_overrides}

        self._rvc = RVCInference(
            device=device,
            model_path=str(pth),
            index_path=str(index) if index else "",
            version=version,
        )
        self._rvc.set_params(
            f0method=self.params["f0method"],
            f0up_key=self.params["f0up_key"],
            index_rate=self.params["index_rate"],
            filter_radius=self.params["filter_radius"],
            resample_sr=self.params["resample_sr"],
            rms_mix_rate=self.params["rms_mix_rate"],
            protect=self.params["protect"],
        )

    def convert_file(self, src: Path, dst: Path) -> Path:
        dst.parent.mkdir(parents=True, exist_ok=True)
        self._rvc.infer_file(str(src), str(dst))
        return dst
