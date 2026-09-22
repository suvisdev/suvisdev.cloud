"""llama.cpp convert_hf_to_gguf.py를 EXAONE 보정과 함께 실행한다.

llama.cpp 304665f(conversion/ 패키지 분리 이후)의 ExaoneModel은
`exaone.attention.layer_norm_rms_epsilon`을 쓰지 않아 llama-quantize가
"key not found"로 실패한다(2026-09-17 코랩·노트북 재현). 09-09 프로덕션 GGUF에는
이 키가 있다(값 = config의 layer_norm_epsilon). 실행 시점에만 한 줄 보충한다.

Usage: python scripts/convert_exaone_gguf.py <llama.cpp 경로> <convert_hf_to_gguf 인자...>
"""

import runpy
import sys

llama = sys.argv[1]
sys.path[:0] = [llama, f"{llama}/gguf-py"]

from conversion import exaone  # noqa: E402

_orig = exaone.ExaoneModel.set_gguf_parameters


def _set_gguf_parameters(self):
    _orig(self)
    self.gguf_writer.add_layer_norm_rms_eps(self.hparams["layer_norm_epsilon"])


exaone.ExaoneModel.set_gguf_parameters = _set_gguf_parameters
sys.argv = [f"{llama}/convert_hf_to_gguf.py", *sys.argv[2:]]
runpy.run_path(sys.argv[0], run_name="__main__")
