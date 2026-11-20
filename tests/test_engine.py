import unittest
import os
from src.models import Scene, Personnage, Stats, Relations
from src.rules_engine import MoteurReglesJDR, ResultatAction

class TestMoteurNarratifEtJDR(unittest.TestCase):

    def setUp(self):
        self.moteur = MoteurReglesJDR()
        
        self.joueur = Personnage(
            id="p_joueur",
            nom="Arthur",
            est_joueur=True,
            caractere="gentil",
            stats=Stats(force=5, dext=4, charisme=6, force_mentale=5, discretion=3, chance=2, stat_arme=3, stat_cosmetics=2),
            relations=Relations(allies=["pnj_roi"], ennemis=["pnj_assassin"])
        )
        
        self.roi = Personnage(
            id="pnj_roi",
            nom="Roi Aldric",
            est_joueur=False,
            caractere="gentil",
            stats=Stats(force=4, dext=2, charisme=8, force_mentale=7, discretion=1, chance=3),
            relations=Relations(allies=["p_joueur", "pnj_garde"], ennemis=["pnj_assassin"])
        )

        self.assassin = Personnage(
            id="pnj_assassin",
            nom="Vesper",
            est_joueur=False,
            caractere="mechant",
            traits_physiques=["borgne_droit"],
            objectif_cache="Empoisonner la coupe du roi",
            stats=Stats(force=6, dext=7, charisme=3, force_mentale=4, discretion=8, chance=2, stat_arme=4),
            relations=Relations(allies=["pnj_garde"], ennemis=["pnj_roi"])
        )

    def test_serialisation_et_deserialisation_scene(self):
        """Vérifie que la sauvegarde et le chargement JSON conservent toutes les données."""
        scene = Scene(
            scene_id="scene_bal_01",
            lieu="Salle de bal royale",
            niveau_danger=3,
            resume_telegraphique="Arthur discute avec le Roi. Vesper observe dans l'ombre.",
            personnages_presents=[self.joueur, self.roi, self.assassin]
        )
        
        fichier_temp = "test_scene_temp.json"
        scene.save_to_file(fichier_temp)
        scene_rechargee = Scene.load_from_file(fichier_temp)
        os.remove(fichier_temp)

        self.assertEqual(scene.scene_id, scene_rechargee.scene_id)
        self.assertEqual(len(scene_rechargee.personnages_presents), 3)
        self.assertEqual(scene_rechargee.personnages_presents[2].objectif_cache, "Empoisonner la coupe du roi")

    def test_filtrage_actions_lecteur(self):
        """Vérifie la distinction entre action neutre et action avec conséquence."""
        self.assertFalse(self.moteur.est_action_avec_consequence("Je scrute la pièce attentivement."))
        self.assertTrue(self.moteur.est_action_avec_consequence("Je lui réponds avec entrain que je suis partant."))

    def test_comportement_gentil_vs_mechant(self):
        """Un personnage gentil ne peut pas attaquer son allié ; un méchant le peut."""
        res_gentil = self.moteur.calculer_degats(self.joueur, self.roi)
        self.assertFalse(res_gentil["autorise"])

        res_mechant = self.moteur.calculer_degats(self.assassin, self.roi, jet_de=15)
        self.assertTrue(res_mechant["autorise"])

    def test_coherence_trait_borgne_degats(self):
        """Attaquer sur la droite d'un personnage borgne du côté droit augmente les dégâts."""
        degats_face = self.moteur.calculer_degats(self.joueur, self.assassin, cote_attaque="face", jet_de=10)
        degats_droite = self.moteur.calculer_degats(self.joueur, self.assassin, cote_attaque="droite", jet_de=10)
        self.assertGreater(degats_droite["degats"], degats_face["degats"])

    def test_maladresse_auto_degats(self):
        """Si le multiplicateur devient négatif (malus élevé), le personnage se blesse."""
        res = self.moteur.calculer_degats(self.joueur, self.assassin, malus=-10, jet_de=2)
        self.assertEqual(res["degats"], 0)
        self.assertGreater(res["auto_degats"], 0)
        self.assertEqual(res["resultat"], ResultatAction.ECHEC_CUISANT)

    def test_calcul_est_mon_ennemi_et_seduction(self):
        """Vérifie la méthode estMonEnnemi (+1 allié commun, -1 ennemi allié de la cible)."""
        # Entre joueur et assassin :
        # Alliés communs : aucun (0)
        # Ennemis du joueur (pnj_assassin) qui sont alliés de l'assassin : aucun (0)
        # Entre roi et assassin :
        # Alliés communs : pnj_garde (+1)
        # Ennemis du roi (pnj_assassin) alliés de l'assassin : aucun (0)
        score_rel = self.moteur.calculer_est_mon_ennemi(self.roi, self.assassin)
        self.assertEqual(score_rel, 1)

        res_seduction = self.moteur.calculer_seduction(self.joueur, self.roi, jet_de=15)
        self.assertEqual(res_seduction["resultat"], ResultatAction.FRANCHE_REUSSITE)

    def test_vol_et_alteration_mentale(self):
        """Vérifie les formules de vol et d'altération mentale."""
        res_vol = self.moteur.calculer_vol(self.assassin, jet_de=10)
        # (8 + 7) * 2 = 30 -> +10 = 40 -> Franche réussite
        self.assertEqual(res_vol["score"], 30)
        self.assertEqual(res_vol["resultat"], ResultatAction.FRANCHE_REUSSITE)

        self.joueur.stats.stat_magie_potion = 3
        res_mental = self.moteur.calculer_alteration_mentale(self.joueur, chance1=2, chance2=1, jet_de=10)
        # (5 + 2) * (3 + 1 + 4) = 7 * 8 = 56
        self.assertEqual(res_mental["score"], 56)

if __name__ == "__main__":
    unittest.main(verbosity=2)
