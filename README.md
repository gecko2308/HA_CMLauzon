# CM Lauzon pour Home Assistant

Surveille les plages de rendez-vous disponibles sur le portail patient (Medfar) de la **Clinique médicale Lévis-Lauzon** et les expose dans Home Assistant.

## Ce que l'intégration crée

Un appareil « Clinique médicale Lévis-Lauzon » avec :

| Entité | Description |
|---|---|
| `sensor.…_prochain_rendez_vous_disponible` | Date et heure de la prochaine plage régulière (attributs : durée, nombre, liste des 20 prochaines plages) |
| `sensor.…_plages_disponibles` | Nombre de plages régulières dans l'horizon de recherche |
| `binary_sensor.…_rendez_vous_disponible` | Activé dès qu'une plage régulière est disponible |
| Équivalents « urgence » | Mêmes entités pour les rendez-vous d'urgence (désactivables dans les options) |

L'événement **`cmlauzon_new_availability`** est émis à chaque nouvelle plage (`type`, `debut`, `duree`) : idéal pour recevoir une notification.

```yaml
# Exemple d'automatisation : notification dès qu'une plage apparaît
triggers:
  - trigger: event
    event_type: cmlauzon_new_availability
    event_data:
      type: regular
actions:
  - action: notify.mobile_app_mon_telephone
    data:
      title: Rendez-vous disponible à la clinique
      message: "{{ as_datetime(trigger.event.data.debut) | as_local }}"
```

## Installation

1. HACS → menu ⋮ → **Dépôts personnalisés** → `https://github.com/gecko2308/HA_CMLauzon`, catégorie **Intégration**.
2. Installez **CM Lauzon**, puis redémarrez Home Assistant.
3. Paramètres → Appareils et services → **Ajouter une intégration** → CM Lauzon, et entrez vos identifiants du portail.

## Options

Fréquence de vérification (15 min par défaut, minimum 5), horizon de recherche (30 jours), suivi des urgences, et identifiants du médecin, du site et des types de rendez-vous (visibles dans l'adresse de la page de réservation du portail).

## Nouveautés de la version 2.0

- Le dossier porte maintenant le nom du domaine (`cmlauzon`) : la version 1.x ne pouvait pas se charger.
- Interrogation périodique (la 1.x ne lisait le portail qu'une seule fois au démarrage) et date de début calculée chaque jour (elle était figée au 27 mai 2025).
- Identifiants vérifiés à la configuration, reconnexion automatique quand la session expire, et demande de nouveau mot de passe dans l'interface si le portail le refuse.
- Entités stables (identifiant unique, appareil, traductions) au lieu d'une entité par plage créée au démarrage.
- Session HTTP gérée par Home Assistant, diagnostics avec identifiants masqués.
