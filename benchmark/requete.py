import time
import requests

# Configuration du benchmark (Port 2020)
BASE_URL = "http://192.168.1.110:2020"  
PROMPT = "Explique-moi la théorie de la relativité en deux phrases."

# Vos modèles à tester
MODELS = [
    "llama3.2:1b",
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "all-minilm:22m",
    "all-minilm:33m",
    "tinyllama:1.1b",
    "llama2.5:3b"
]

def benchmark_model(model_name, prompt):
    # Changement pour l'API compatible OpenAI (v1) qui résout l'erreur 404
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    # Structure de la requête OpenAI
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "stream": False  
    }
    
    print(f"🔄 Interrogation du modèle : {model_name}...")
    
    # Enregistrement du temps de départ
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # Calcul du temps écoulé
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            return elapsed_time
        else:
            print(f"❌ Erreur {response.status_code} pour {model_name}: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Impossible de contacter le serveur sur le port 2020 pour {model_name}: {e}")
        return None

def main():
    print(f"🚀 Début du benchmark sur {len(MODELS)} modèles")
    print(f"❓ Question posée : \"{PROMPT}\"\n" + "-"*40)
    
    results = {}
    
    for model in MODELS:
        elapsed = benchmark_model(model, PROMPT)
        if elapsed is not None:
            results[model] = elapsed
            print(f"⏱️  Temps de réponse : {elapsed:.2f} secondes\n")
    
    # Affichage du classement final
    print("="*40)
    print("🏆 RÉSULTATS DU BENCHMARK (Du plus rapide au plus lent)")
    print("="*40)
    
    # Tri correct basé sur la deuxième valeur (le temps de réponse)
    sorted_results = sorted(results.items(), key=lambda x: x[1])
    for rank, (model, t) in enumerate(sorted_results, 1):
        print(f"{rank}. {model:<15} : {t:.2f} secondes")

if __name__ == "__main__":
    main()
