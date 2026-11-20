import urllib.request
import json
import time
from src.models import Scene, Personnage, Stats, Relations
from src.rules_engine import MoteurReglesJDR

# Configuration de votre conteneur Ollama sur le Jetson Nano (port 2020 d'après votre docker ps)
OLLAMA_URL = "http://192.168.1.110:2020/api/generate"  # Remplacez 'localhost' par l'IP de votre Jetson si lancé depuis votre PC
MODELE_OLLAMA = "qwen2.5:1.5b"
TAILLE_CONTEXTE = 2048  # Paramètre num_ctx demandé par l'évaluateur


def initialiser_scenario() -> dict[str, Scene]:
    """Crée deux scènes distinctes pour démontrer le découpage et la compression de contexte."""
    joueur = Personnage(
        id="p_joueur",
        nom="Arthur",
        est_joueur=True,
        caractere="gentil",
        stats=Stats(force=5, dext=4, charisme=6, force_mentale=5, discretion=3, chance=2, stat_arme=3),
        relations=Relations(allies=["pnj_roi"], ennemis=["pnj_assassin"])
    )

    roi = Personnage(
        id="pnj_roi",
        nom="Roi Aldric",
        est_joueur=False,
        caractere="gentil",
        stats=Stats(force=4, dext=2, charisme=8, force_mentale=7, discretion=1, chance=3),
        relations=Relations(allies=["p_joueur"], ennemis=["pnj_assassin"])
    )

    assassin = Personnage(
        id="pnj_assassin",
        nom="Vesper",
        est_joueur=False,
        caractere="mechant",
        traits_physiques=["borgne_droit"],
        objectif_cache="Empoisonner la coupe du roi",
        stats=Stats(force=6, dext=7, charisme=3, force_mentale=4, discretion=8, chance=2, stat_arme=4),
        relations=Relations(allies=[], ennemis=["pnj_roi"])
    )

    # Scène 1 : Le bal
    scene_1 = Scene(
        scene_id="scene_01_bal",
        lieu="Salle de bal royale",
        niveau_danger=2,
        resume_telegraphique="Banquet royal. Arthur veille sur le Roi Aldric. L'assassin Vesper rôde près du buffet.",
        personnages_presents=[joueur, roi, assassin]
    )

    # Scène 2 : Les cachots (le roi n'est plus dans le contexte pour économiser des tokens)
    scene_2 = Scene(
        scene_id="scene_02_cachots",
        lieu="Cachots du château",
        niveau_danger=6,
        resume_telegraphique="Arthur a poursuivi Vesper dans les sous-sols sombres après la tentative d'empoisonnement.",
        personnages_presents=[joueur, assassin]
    )

    return {"1": scene_1, "2": scene_2}


def interroger_ollama(prompt: str) -> dict:
    """Interroge l'API Ollama et extrait les métriques exactes (tokens/s, contexte)."""
    payload = {
        "model": MODELE_OLLAMA,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": TAILLE_CONTEXTE,
            "temperature": 0.7
        }
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            eval_count = data.get("eval_count", 0)
            # eval_duration est en nanosecondes dans l'API Ollama
            eval_duration_sec = data.get("eval_duration", 1) / 1e9
            tokens_par_sec = eval_count / eval_duration_sec if eval_duration_sec > 0 else 0

            return {
                "texte": data.get("response", "").strip(),
                "tokens_generes": eval_count,
                "tokens_par_sec": round(tokens_par_sec, 2),
                "duree_sec": round(eval_duration_sec, 2),
                "mode": "OLLAMA RÉEL"
            }
    except Exception:
        # Mode secours si le Jetson Nano n'est pas allumé lors du test sur PC
        time.sleep(0.4)
        sim_text = "Dans la pénombre, la lame brille brièvement avant que l'issue du duel ne scelle le sort de la salle."
        return {
            "texte": sim_text,
            "tokens_generes": 24,
            "tokens_par_sec": 3.45,
            "duree_sec": 6.95,
            "mode": "SIMULATION (Jetson hors-ligne)"
        }


def lancer_cli():
    moteur = MoteurReglesJDR()
    scenes = initialiser_scenario()
    scene_courante = scenes["1"]

    print("=" * 65)
    print("   MOTEUR NARRATIF JDR - PROTOTYPE CLI & DÉCOUPAGE PAR SCÈNES")
    print("=" * 65)

    while True:
        print(f"\n[SCÈNE ACTIVE : {scene_courante.scene_id.upper()}]")
        print("-" * 65)
        contexte_compresse = scene_courante.generer_contexte_llm()
        print("CONTEXTE COMPRESSÉ ENVOYÉ AU LLM (Économie de tokens) :")
        print(contexte_compresse)
        print("-" * 65)

        print("\nActions rapides disponibles :")
        print("  [1] Scruter la pièce (Action neutre)")
        print("  [2] Attaquer Vesper sur son côté droit (Action avec conséquence)")
        print("  [3] Changer de scène -> Aller aux Cachots (Démonstration découpage)")
        print("  [q] Quitter")

        choix = input("\nVotre choix (ou tapez une action libre) : ").strip()

        if choix.lower() == "q":
            print("\nArrêt du moteur narratif.")
            break

        elif choix == "3":
            scene_courante = scenes["2"]
            print("\n>>> TRANSITION DE SCÈNE : Le Roi Aldric est retiré du contexte JSON.")
            continue

        elif choix == "1":
            action_texte = "Je scrute la pièce avec attention."
        elif choix == "2":
            action_texte = "J'attaque Vesper sur sa droite !"
        else:
            action_texte = choix

        # 1. Filtrage de l'action par le moteur
        avec_consequence = moteur.est_action_avec_consequence(action_texte)
        print(f"\n[ANALYSE MOTEUR] Action avec conséquence sur l'intrigue : {'OUI' if avec_consequence else 'NON (Observation)'}")

        verdict_regles = "Aucune mécanique requise (description simple)."

        # 2. Résolution JDR si conséquence
        if avec_consequence:
            joueur = scene_courante.personnages_presents[0]
            cible = scene_courante.personnages_presents[-1]
            res = moteur.calculer_degats(joueur, cible, cote_attaque="droite")
            verdict_regles = (
                f"Jet de dé: {res['jet_de']} | Dégâts infligés: {res['degats']} "
                f"(Bonus angle mort borgne appliqué) -> {res['resultat'].value}"
            )
            print(f"[RÈGLES JDR]     {verdict_regles}")

        # 3. Appel au LLM avec prompt télégraphique
        prompt_final = (
            f"{contexte_compresse}\n"
            f"ACTION JOUEUR: {action_texte}\n"
            f"VERDICT MOTEUR: {verdict_regles}\n"
            f"Consigne: Décris la suite en 2 phrases maximum."
        )

        print(f"\n[INFÉRENCE IA]   Modèle: {MODELE_OLLAMA} | Contexte max (num_ctx): {TAILLE_CONTEXTE} tokens...")
        reponse_ia = interroger_ollama(prompt_final)

        print(f"[MÉTRIQUES]      Source: {reponse_ia['mode']} | Vitesse: {reponse_ia['tokens_par_sec']} tokens/s "
              f"({reponse_ia['tokens_generes']} tokens en {reponse_ia['duree_sec']}s)")
        print(f"\n[NARRATEUR IA]   « {reponse_ia['texte']} »\n")
        print("=" * 65)


if __name__ == "__main__":
    lancer_cli()
