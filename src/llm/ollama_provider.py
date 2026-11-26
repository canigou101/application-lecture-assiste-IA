import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any
from src.llm.base_provider import ILLMProvider


class OllamaProvider(ILLMProvider):
    """
    Fournisseur local ou LAN (PC local sur port 11434 ou Jetson Nano sur port 2020).
    Assure une confidentialité totale (100% hors-ligne / réseau local).
    """

    def __init__(self, base_url: str = "http://localhost:11434", modele: str = "qwen2.5:1.5b"):
        self.endpoint = f"{base_url.rstrip('/')}/api/generate"
        self.modele = modele

    def generer_narration(self, prompt: str, num_ctx: int = 2048) -> Dict[str, Any]:
        payload = {
            "model": self.modele,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "temperature": 0.7
            }
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        debut = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)

                if eval_duration_ns > 0:
                    duree_sec = eval_duration_ns / 1e9
                else:
                    duree_sec = max(time.perf_counter() - debut, 0.01)

                tokens_par_sec = eval_count / duree_sec if duree_sec > 0 else 0.0

                return {
                    "texte": data.get("response", "").strip(),
                    "tokens_generes": eval_count,
                    "tokens_par_sec": round(tokens_par_sec, 2),
                    "duree_sec": round(duree_sec, 2),
                    "source": f"OLLAMA LOCAL/LAN ({self.modele})"
                }
        except urllib.error.URLError as e:
            raise ConnectionError(f"Impossible de joindre Ollama sur {self.endpoint} : {e}")
