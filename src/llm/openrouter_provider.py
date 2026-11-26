import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any
from src.llm.base_provider import ILLMProvider


class OpenRouterProvider(ILLMProvider):
    """
    Fournisseur API distante via OpenRouter (modèles plus puissants ou gratuits).
    """

    ENDPOINT = "https://openrouter.ai"

    def __init__(
        self,
        api_key: str,
        modele: str = "qwen/qwen-2.5-7b-instruct:free",
        app_name: str = "Application-Lecture-Assistee-IA"
    ):
        if not api_key or not api_key.strip():
            raise ValueError("Une clé API OpenRouter valide est requise.")
        self.api_key = api_key.strip()
        self.modele = modele
        self.app_name = app_name

    def generer_narration(self, prompt: str, num_ctx: int = 2048) -> Dict[str, Any]:
        payload = {
            "model": self.modele,
            "messages": [
                {
                    "role": "system",
                    "content": "Tu es le narrateur concis d'un JDR interactif. Respecte strictement le verdict du moteur de règles."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": min(250, num_ctx // 4),
            "temperature": 0.7
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com",
            "X-Title": self.app_name
        }

        req = urllib.request.Request(
            self.ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        debut = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
                duree_sec = max(time.perf_counter() - debut, 0.01)

                texte = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})
                tokens_generes = usage.get("completion_tokens", len(texte.split()))
                tokens_par_sec = tokens_generes / duree_sec

                return {
                    "texte": texte,
                    "tokens_generes": tokens_generes,
                    "tokens_par_sec": round(tokens_par_sec, 2),
                    "duree_sec": round(duree_sec, 2),
                    "source": f"OPENROUTER API ({self.modele})"
                }
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Erreur HTTP OpenRouter ({e.code}) : {detail}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Erreur réseau vers OpenRouter : {e}")
