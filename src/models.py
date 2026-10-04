"""Model loading and sampling, shared by run.py and probe.py.

Factored out so the recognition probe reuses the runner's loading and sampling
rather than reimplementing them -- two copies of sampling logic is two chances
for the probe and the main run to differ in a way that invalidates comparing
them.

Weights are 4-bit. Qwen2.5-7B-Instruct at fp16 is roughly 15GB and does not fit
in this machine's 8GB of unified memory, so quantisation is forced rather than
chosen. It is a documented deviation from the models named in the brief and
belongs in summary.md as a limitation: a 4-bit model is not the fp16 model, and
nothing here establishes that quantisation is neutral for name bias.
"""

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

# 7B is listed for completeness but not run: on this 8GB machine it swapped
# (~9.6s per call against 1.9s for 3B) and froze the system at 123/600 calls.
# Its partial output is kept in results/raw_7b_partial_abandoned.jsonl.
MODELS = {
    "qwen2.5-3b": "mlx-community/Qwen2.5-3B-Instruct-4bit",
    "qwen2.5-7b": "mlx-community/Qwen2.5-7B-Instruct-4bit",
    # The size used in the reference paper. Small enough to run unquantised in
    # 8GB, so it is loaded in bf16 -- the official release's own precision --
    # and carries no quantisation caveat, unlike the 3B runs.
    "qwen2.5-1.5b": "mlx-community/Qwen2.5-1.5B-Instruct-bf16",
}

DEFAULT_MODELS = ["qwen2.5-3b"]

TEMPERATURE = 0.7
MAX_TOKENS = 160


class Model:
    """One loaded model. Load one at a time -- 8GB will not hold both."""

    def __init__(self, name):
        if name not in MODELS:
            raise ValueError(f"unknown model {name!r}; expected one of {list(MODELS)}")
        self.name = name
        self.repo = MODELS[name]
        self.model, self.tokenizer = load(self.repo)
        self.sampler = make_sampler(temp=TEMPERATURE)

    def complete(self, prompt):
        """Chat-formatted completion at the fixed sampling temperature."""
        text = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True, tokenize=False)
        return generate(self.model, self.tokenizer, prompt=text,
                        max_tokens=MAX_TOKENS, sampler=self.sampler,
                        verbose=False)
