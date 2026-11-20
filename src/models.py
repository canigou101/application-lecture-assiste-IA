import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class Stats:
    force: int
    dext: int
    charisme: int
    force_mentale: int
    discretion: int
    chance: int
    stat_arme: int = 0
    stat_cosmetics: int = 0
    stat_magie_potion: int = 0

@dataclass
class Relations:
    allies: List[str] = field(default_factory=list)
    ennemis: List[str] = field(default_factory=list)

@dataclass
class Personnage:
    id: str
    nom: str
    est_joueur: bool
    caractere: str  # "gentil", "neutre", "mechant"
    stats: Stats
    traits_physiques: List[str] = field(default_factory=list)
    relations: Relations = field(default_factory=Relations)
    objectif_cache: Optional[str] = None

@dataclass
class Scene:
    scene_id: str
    lieu: str
    niveau_danger: int
    resume_telegraphique: str
    personnages_presents: List[Personnage] = field(default_factory=list)

    def to_json(self) -> str:
        """Sérialise la scène en chaîne JSON formatée."""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def save_to_file(self, filepath: str) -> None:
        """Sauvegarde la scène dans un fichier JSON."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def from_json(cls, json_str: str) -> "Scene":
        """Désérialise une chaîne JSON en objet Scene."""
        data = json.loads(json_str)
        personnages = []
        for p in data["personnages_presents"]:
            stats_obj = Stats(**p["stats"])
            rel_obj = Relations(**p["relations"])
            personnages.append(
                Personnage(
                    id=p["id"],
                    nom=p["nom"],
                    est_joueur=p["est_joueur"],
                    caractere=p["caractere"],
                    traits_physiques=p.get("traits_physiques", []),
                    objectif_cache=p.get("objectif_cache"),
                    stats=stats_obj,
                    relations=rel_obj
                )
            )
        return cls(
            scene_id=data["scene_id"],
            lieu=data["lieu"],
            niveau_danger=data["niveau_danger"],
            resume_telegraphique=data["resume_telegraphique"],
            personnages_presents=personnages
        )

    @classmethod
    def load_from_file(cls, filepath: str) -> "Scene":
        """Charge une scène depuis un fichier JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def generer_contexte_llm(self) -> str:
        """Compresse la scène en style télégraphique pour économiser des tokens sur Ollama."""
        lignes = [
            f"LIEU: {self.lieu} (Danger: {self.niveau_danger}/10)",
            f"HISTORIQUE: {self.resume_telegraphique}",
            "PERSONNAGES:"
        ]
        for p in self.personnages_presents:
            traits = ", ".join(p.traits_physiques) if p.traits_physiques else "aucun"
            lignes.append(f"- {p.nom} [{p.caractere}] | Traits: {traits}")
        return "\n".join(lignes)
