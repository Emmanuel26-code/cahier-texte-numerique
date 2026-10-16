"""Tâche 50 : notifications aux élèves (nouveau travail à faire, nouveau plan de cours)."""
from datetime import date

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.academique.models import Affectation, Classe, Matiere
from apps.cahier.models import Seance
from apps.plans.models import Plan
from apps.comptes.models import Utilisateur
from apps.notifications.models import Notification

Role = Utilisateur.Role
Type = Notification.Type


class BaseNotifications(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.classe_a = Classe.objects.create(nom="6e A")
        cls.classe_b = Classe.objects.create(nom="5e B")
        maths = Matiere.objects.create(nom="Mathématiques")
        cls.prof = Utilisateur.objects.create_user("prof", password="x", role=Role.PROFESSEUR)
        cls.admin = Utilisateur.objects.create_user("admin1", password="x", role=Role.ADMINISTRATEUR)
        cls.aff_a = Affectation.objects.create(professeur=cls.prof, classe=cls.classe_a, matiere=maths)
        cls.aff_b = Affectation.objects.create(professeur=cls.prof, classe=cls.classe_b, matiere=maths)
        cls.awa = Utilisateur.objects.create_user("awa", password="x", role=Role.ELEVE, classe=cls.classe_a)
        cls.koffi = Utilisateur.objects.create_user("koffi", password="x", role=Role.ELEVE, classe=cls.classe_a)
        cls.fatou = Utilisateur.objects.create_user("fatou", password="x", role=Role.ELEVE, classe=cls.classe_b)

    def seance(self, affectation=None, **kw):
        kw.setdefault("titre", "Addition de fractions")
        return Seance.objects.create(affectation=affectation or self.aff_a, date=date(2026, 10, 12), **kw)


class DeclencheursTravailTests(BaseNotifications):
    def test_nouveau_travail_notifie_les_eleves_de_la_classe_uniquement(self):
        self.seance(travail_a_faire="Exercices 4 à 7, page 52")
        self.assertEqual(Notification.objects.filter(destinataire=self.awa, type=Type.TRAVAIL).count(), 1)
        self.assertEqual(Notification.objects.filter(destinataire=self.koffi, type=Type.TRAVAIL).count(), 1)
        self.assertFalse(Notification.objects.filter(destinataire=self.fatou).exists())   # autre classe
        self.assertFalse(Notification.objects.filter(destinataire=self.prof).exists())    # pas le professeur
        self.assertFalse(Notification.objects.filter(destinataire=self.admin).exists())   # pas l'administrateur

    def test_le_message_contient_la_matiere_et_un_extrait(self):
        self.seance(travail_a_faire="Exercices 4 à 7, page 52")
        message = Notification.objects.get(destinataire=self.awa).message
        self.assertIn("Mathématiques", message)
        self.assertIn("Exercices 4 à 7, page 52", message)

    def test_un_long_travail_est_tronque(self):
        self.seance(travail_a_faire="mot " * 100)
        message = Notification.objects.get(destinataire=self.awa).message
        self.assertLessEqual(len(message), 255)
        self.assertTrue(message.endswith("…"))

    def test_seance_sans_travail_ne_notifie_personne(self):
        self.seance()
        self.assertEqual(Notification.objects.count(), 0)

    def test_travail_ajoute_plus_tard_notifie_une_fois(self):
        s = self.seance()
        s.travail_a_faire = "Apprendre la leçon 3"
        s.save()
        self.assertEqual(Notification.objects.filter(destinataire=self.awa).count(), 1)

    def test_modifier_une_seance_deja_avec_travail_ne_renvoie_rien(self):
        s = self.seance(travail_a_faire="Leçon 3")
        s.titre = "Titre corrigé"
        s.save()
        s.travail_a_faire = "Leçon 3 et 4"
        s.save()
        self.assertEqual(Notification.objects.filter(destinataire=self.awa).count(), 1)

    def test_eleve_inactif_ou_sans_classe_non_notifie(self):
        Utilisateur.objects.create_user("inactif", password="x", role=Role.ELEVE, classe=self.classe_a, is_active=False)
        Utilisateur.objects.create_user("sans_classe", password="x", role=Role.ELEVE)
        self.seance(travail_a_faire="Leçon 3")
        self.assertEqual(Notification.objects.count(), 2)  # awa et koffi seulement

    def test_nombre_de_requetes_independant_du_nombre_d_eleves(self):
        def mesurer(classe, nb_eleves):
            maths = Matiere.objects.first()
            aff = Affectation.objects.create(professeur=self.prof, classe=classe, matiere=maths)
            for i in range(nb_eleves):
                Utilisateur.objects.create_user(f"{classe.nom}-{nb_eleves}-{i}", password="x", role=Role.ELEVE, classe=classe)
            with CaptureQueriesContext(connection) as ctx:
                Seance.objects.create(affectation=aff, date=date(2026, 10, 12), titre="t", travail_a_faire="x")
            return len(ctx)
        petite = mesurer(Classe.objects.create(nom="petite"), 2)
        grande = mesurer(Classe.objects.create(nom="grande"), 30)
        self.assertEqual(petite, grande)


class DeclencheursPlanTests(BaseNotifications):
    def plan(self, statut=Plan.Statut.BROUILLON):
        return Plan.objects.create(affectation=self.aff_a, titre="Chapitre 6 : Les fractions", statut=statut)

    def test_brouillon_ne_notifie_pas(self):
        self.plan()
        self.assertEqual(Notification.objects.count(), 0)

    def test_validation_notifie_les_eleves_de_la_classe(self):
        p = self.plan()
        p.statut = Plan.Statut.VALIDE
        p.save()
        self.assertEqual(Notification.objects.filter(type=Type.PLAN).count(), 2)
        self.assertFalse(Notification.objects.filter(destinataire=self.fatou).exists())
        self.assertIn("Chapitre 6", Notification.objects.get(destinataire=self.awa).message)

    def test_plan_cree_directement_valide_notifie(self):
        self.plan(Plan.Statut.VALIDE)
        self.assertEqual(Notification.objects.filter(destinataire=self.awa, type=Type.PLAN).count(), 1)

    def test_resauvegarder_un_plan_valide_ne_renvoie_rien(self):
        p = self.plan(Plan.Statut.VALIDE)
        p.titre = "Titre modifié"
        p.save()
        self.assertEqual(Notification.objects.filter(destinataire=self.awa).count(), 1)

    def test_plan_rejete_ne_notifie_pas(self):
        p = self.plan()
        p.statut = Plan.Statut.REJETE
        p.save()
        self.assertEqual(Notification.objects.count(), 0)


class PagesNotificationsTests(BaseNotifications):
    def test_liste_montre_seulement_mes_notifications_recentes_d_abord(self):
        Notification.objects.create(destinataire=self.awa, type=Type.TRAVAIL, message="Ancienne")
        Notification.objects.create(destinataire=self.awa, type=Type.PLAN, message="Récente")
        Notification.objects.create(destinataire=self.koffi, type=Type.TRAVAIL, message="Celle de Koffi")
        self.client.force_login(self.awa)
        reponse = self.client.get(reverse("notifications:liste"))
        self.assertNotContains(reponse, "Celle de Koffi")
        self.assertEqual([n.message for n in reponse.context["notifications"]], ["Récente", "Ancienne"])

    def test_message_quand_aucune_notification(self):
        self.client.force_login(self.awa)
        self.assertContains(self.client.get(reverse("notifications:liste")), "Aucune notification pour le moment.")

    def test_marquer_une_notification_lue(self):
        n = Notification.objects.create(destinataire=self.awa, type=Type.TRAVAIL, message="x")
        self.client.force_login(self.awa)
        reponse = self.client.post(reverse("notifications:marquer_lue", args=[n.pk]))
        self.assertRedirects(reponse, reverse("notifications:liste"), fetch_redirect_response=False)
        n.refresh_from_db()
        self.assertTrue(n.lue)

    def test_impossible_de_marquer_la_notification_d_un_autre_eleve(self):
        n = Notification.objects.create(destinataire=self.koffi, type=Type.TRAVAIL, message="x")
        self.client.force_login(self.awa)
        self.assertEqual(self.client.post(reverse("notifications:marquer_lue", args=[n.pk])).status_code, 404)
        n.refresh_from_db()
        self.assertFalse(n.lue)

    def test_marquer_lue_refuse_la_methode_get(self):
        n = Notification.objects.create(destinataire=self.awa, type=Type.TRAVAIL, message="x")
        self.client.force_login(self.awa)
        self.assertEqual(self.client.get(reverse("notifications:marquer_lue", args=[n.pk])).status_code, 405)

    def test_tout_marquer_lu_ne_touche_que_mes_notifications(self):
        Notification.objects.create(destinataire=self.awa, type=Type.TRAVAIL, message="a")
        Notification.objects.create(destinataire=self.awa, type=Type.PLAN, message="b")
        autre = Notification.objects.create(destinataire=self.koffi, type=Type.TRAVAIL, message="c")
        self.client.force_login(self.awa)
        self.client.post(reverse("notifications:tout_lire"))
        self.assertEqual(Notification.objects.filter(destinataire=self.awa, lue=False).count(), 0)
        autre.refresh_from_db()
        self.assertFalse(autre.lue)

    def test_pastille_du_tableau_de_bord_compte_les_non_lues(self):
        Notification.objects.create(destinataire=self.awa, type=Type.TRAVAIL, message="a")
        Notification.objects.create(destinataire=self.awa, type=Type.PLAN, message="b")
        Notification.objects.create(destinataire=self.awa, type=Type.PLAN, message="c", lue=True)
        self.client.force_login(self.awa)
        reponse = self.client.get(reverse("tableau_de_bord:eleve"))
        self.assertEqual(reponse.context["nb_non_lues"], 2)
        self.assertContains(reponse, "Notifications : 2 non lues")

    def test_pages_reservees_aux_eleves(self):
        urls = [reverse("notifications:liste"), reverse("notifications:tout_lire")]
        for compte in (self.prof, self.admin):
            self.client.force_login(compte)
            for url in urls:
                with self.subTest(compte=compte.role, url=url):
                    reponse = self.client.post(url) if "tout-lire" in url else self.client.get(url)
                    self.assertContains(reponse, "Accès interdit", status_code=403)
        self.client.logout()
        for url in urls:
            with self.subTest(visiteur=True, url=url):
                reponse = self.client.get(url)
                self.assertRedirects(reponse, f"{reverse('comptes:connexion')}?next={url}", fetch_redirect_response=False)
