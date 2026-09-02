"""LATEST LoRA 어댑터를 베이스에 병합해 GGUF로 굽는다 — llama.cpp 서빙용.

재학습 후 실행하는 후처리 단계다: train_mova_lora.py가 갱신한
~/lora_adapters/LATEST(어댑터 경로/백엔드/베이스 경로)를 읽어
① 베이스 fp16 + 어댑터 병합(GPU) → HF 형식 저장
② convert_hf_to_gguf.py로 f16 GGUF 변환(CPU)
③ llama-quantize로 양자화(CPU, 기본 Q5_K_M)
④ ~/lora_adapters/LATEST_GGUF에 최종 GGUF 경로 기록(서빙이 이 파일을 읽음)

①은 VRAM ~5GB가 필요하므로 lora-server를 먼저 내리고 실행할 것:
  systemctl --user stop lora-server
  python scripts/export_mova_gguf.py
  systemctl --user start lora-server   # nvidia-smi로 VRAM 하강 확인 후

중간 산출물(병합 HF 디렉터리, f16 GGUF)은 검증 편의를 위해 남긴다 —
디스크가 아쉬우면 수동 삭제해도 된다(GGUF만 있으면 서빙엔 충분).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_LATEST = Path.home() / "lora_adapters" / "LATEST"
_LATEST_GGUF = Path.home() / "lora_adapters" / "LATEST_GGUF"
_LLAMA_CPP_DIR = Path(os.getenv("LLAMA_CPP_DIR", str(Path.home() / "llama.cpp")))
_QUANTIZE_BIN = Path(
    os.getenv("LLAMA_QUANTIZE_BIN", str(Path.home() / "llama-cpu/llama-b10754/llama-quantize"))
)


def _read_latest() -> tuple[Path, str, Path]:
    adapter_dir, backend, base_model = _LATEST.read_text(encoding="utf-8").splitlines()[:3]
    return Path(adapter_dir), backend, Path(base_model)


def _merge_and_save(adapter_dir: Path, base_model: Path, merged_dir: Path) -> None:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[export] 베이스 로드: {base_model}")
    base = AutoModelForCausalLM.from_pretrained(
        base_model, torch_dtype=torch.float16, device_map="cuda:0", trust_remote_code=True
    )
    print(f"[export] 어댑터 병합: {adapter_dir}")
    merged = PeftModel.from_pretrained(base, str(adapter_dir)).merge_and_unload()
    print(f"[export] 병합 모델 저장: {merged_dir}")
    merged.save_pretrained(str(merged_dir), max_shard_size="1GB")
    AutoTokenizer.from_pretrained(base_model, trust_remote_code=True).save_pretrained(
        str(merged_dir)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=Path("/mnt/d/models/gguf"))
    parser.add_argument("--quant", default="Q5_K_M")
    args = parser.parse_args()

    adapter_dir, backend, base_model = _read_latest()
    if backend != "plain":
        sys.exit(f"[export] plain(fp16) 백엔드만 지원 — LATEST의 백엔드: {backend}")
    version = adapter_dir.name  # 예: mova_20260902_055400

    args.out_root.mkdir(parents=True, exist_ok=True)
    merged_dir = args.out_root / f"{version}-merged"
    f16_gguf = args.out_root / f"{version}-f16.gguf"
    out_gguf = args.out_root / f"{version}-{args.quant}.gguf"

    if not merged_dir.exists():
        _merge_and_save(adapter_dir, base_model, merged_dir)
    else:
        print(f"[export] 병합 디렉터리 재사용: {merged_dir}")

    print(f"[export] GGUF 변환: {f16_gguf}")
    subprocess.run(
        [
            sys.executable,
            str(_LLAMA_CPP_DIR / "convert_hf_to_gguf.py"),
            str(merged_dir),
            "--outfile",
            str(f16_gguf),
            "--outtype",
            "f16",
        ],
        check=True,
    )

    print(f"[export] 양자화({args.quant}): {out_gguf}")
    subprocess.run([str(_QUANTIZE_BIN), str(f16_gguf), str(out_gguf), args.quant], check=True)

    _LATEST_GGUF.write_text(f"{out_gguf}\n", encoding="utf-8")
    print(f"[export] 완료: {out_gguf}")
    print(f"[export] LATEST_GGUF 갱신: {_LATEST_GGUF}")


if __name__ == "__main__":
    main()
