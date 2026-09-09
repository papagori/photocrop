# Validation — Photo Crop V2

Date : 9 septembre 2026. Windows x64, Python 3.10.6, Pillow 12.3.0, PySide6 6.11.0, PyInstaller 6.20.0.

## Point de restauration initial

Avant toute modification fonctionnelle : **9 tests réussis**. Le `.gitignore` a été complété, le dépôt Git initialisé, puis le commit **656aa11** et le tag **v1.0-baseline** créés.

L'archive **backups/PhotoCrop4x3-v1.0-656aa11.zip** contient 19 fichiers du projet initial, notamment les sources et l'ancien EXE, plus un manifeste SHA-256 et les dépendances figées. Elle exclut Git, l'environnement virtuel, le build et les caches. Lecture ZIP complète et comparaison des empreintes de tous les fichiers : **réussies**, avant de commencer l'évolution.

## Tests automatisés V2

Commande : `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

**21 tests réussis**, en 8,924 secondes lors de l'exécution de validation.

- Les 9 tests de la version initiale continuent de passer : paysage/portrait/carré, exactitude et centrage, EXIF (8 orientations), ICC, quantification JPEG, intégrité des originaux, formats, transparence, collisions, dossiers, Unicode, corruption et batch Qt avec drag & drop.
- Tous les nouveaux ratios sont vérifiés en paysage, portrait et carré, y compris la réduction correcte de 21:9 en 7:3 et 16:10 en 8:5.
- Tous les presets sont vérifiés pour leurs dimensions, leur inversion portrait et la protection contre l'agrandissement.
- Exemples 4K : 4:3 → 4096 × 3072 et 3072 × 4096 ; 16:9 → 4096 × 2304 et 2304 × 4096.
- Original Resolution n'appelle jamais resize ; No Crop conserve les dimensions, y compris une image de 1 × 2 px.
- Un appel unique LANCZOS est vérifié, après crop, avec réduction intermédiaire désactivée.
- La protection contre l'agrandissement compare la cible à l'image après crop, et non à la taille source.
- Les presets exacts imposent leur ratio, y compris sur une image EXIF portrait ; les dimensions EXIF finales et le profil ICC sont vérifiés après resize.
- Les presets approximatifs évitent les crops excessifs et produisent leurs dimensions exactes lorsqu'un resize est autorisé.
- Une image avec palette et transparence est composée et filtrée correctement avant export.
- Les menus Qt se synchronisent, affichent les ratios spéciaux, verrouillent les options pendant le worker et produisent la taille attendue dans le batch.

Capture examinée visuellement : **test-results/gui-v2-tested.png**.

## Contrôle du binaire autonome

Compilation `--onefile --windowed --name PhotoCropV2` : **réussie**.

Exécution réelle de **dist/PhotoCropV2.exe --self-test test-results/compiled-v2.json** : **code de sortie 0**, `passed: true`, `frozen: true`.

Le mode de contrôle instancie la vraie interface Qt avec le plugin offscreen, pilote ses menus et boutons et exécute son worker sur des images synthétiques temporaires dans un chemin accentué/japonais. Aucun Python externe n'est nécessaire pour exécuter ce contrôle du binaire.

| Batch compilé | Paysage | Portrait | Résultat |
| --- | --- | --- | --- |
| 16:9, grand côté 1024, agrandissement interdit | 592 × 333 | 333 × 592 | 2 images traitées |
| 16:9, grand côté 1024, agrandissement autorisé | 1024 × 576 | 576 × 1024 | 2 images traitées |
| Preset exact 1200 × 800, ratio auto 3:2 | 1200 × 800 | 800 × 1200 | 2 images traitées |

Chaque batch contient aussi un faux JPEG corrompu : une erreur attendue, sans interruption des deux autres images. Les fichiers de sortie sont rouverts et leurs dimensions vérifiées. Les trois passes vérifient aussi les suffixes anti-écrasement.

Rapport complet : **test-results/compiled-v2.json** ; capture : **test-results/compiled-v2.png**. Le contrôle binaire est réalisé sans clics Windows physiques ; les événements drag & drop sont couverts par les tests Qt depuis les sources.

## Limites explicites

L'absence d'agrandissement prime sur la taille exacte demandée. Les ratios non représentables avec des dimensions entières nécessitent un arrondi au pixel et, au resize, une correction de bord liée à cet arrondi. JPEG reste avec pertes, même à qualité 100. Les limites de formats de la version initiale sont conservées et décrites dans README.md.
