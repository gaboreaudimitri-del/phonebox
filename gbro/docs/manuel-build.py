from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether, NextPageTemplate)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-I", F + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "DejaVuSansMono.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("Sans", 0, 0, "Sans"); addMapping("Sans", 1, 0, "Sans-B"); addMapping("Sans", 0, 1, "Sans-I"); addMapping("Sans", 1, 1, "Sans-B")

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#475569")
ACCENT = colors.HexColor("#65a30d")
NEON = colors.HexColor("#a3e635")
DARK = colors.HexColor("#0b1120")
SOFT = colors.HexColor("#f1f5f9")
WARN_BG = colors.HexColor("#fff7ed"); WARN = colors.HexColor("#c2410c")
INFO_BG = colors.HexColor("#f0fdf4")
LINE = colors.HexColor("#e2e8f0")

APK = "https://github.com/gaboreaudimitri-del/phonebox/releases/download/bluetooth-latest/PhoneBox-Bluetooth.apk"
ZIP = "https://github.com/gaboreaudimitri-del/phonebox/releases/download/bluetooth-latest/PhoneBox-Bluetooth-Windows.zip"
PAGE = "https://github.com/gaboreaudimitri-del/phonebox/releases/tag/bluetooth-latest"
CLAUDE_DOC = "https://code.claude.com/docs/en/setup"

body = ParagraphStyle("body", fontName="Sans", fontSize=10.5, leading=15, textColor=INK, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=9, leading=12.5, textColor=MUTED)
h1 = ParagraphStyle("h1", fontName="Sans-B", fontSize=17, leading=22, textColor=INK, spaceBefore=4, spaceAfter=10)
h2 = ParagraphStyle("h2", fontName="Sans-B", fontSize=12.5, leading=17, textColor=ACCENT, spaceBefore=10, spaceAfter=5)
step = ParagraphStyle("step", parent=body, leftIndent=16, firstLineIndent=-16, spaceAfter=5)
code = ParagraphStyle("code", fontName="Mono", fontSize=8.8, leading=12, textColor=INK, backColor=SOFT,
                      borderPadding=(5, 6, 5, 6), spaceBefore=3, spaceAfter=9, leftIndent=6, rightIndent=6)
cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=13, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Sans-B")


def link(url, text=None):
    return f'<link href="{url}" color="#4d7c0f"><u>{text or url}</u></link>'


def box(text, bg=INFO_BG, edge=ACCENT, title=None):
    content = [Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", parent=body, textColor=edge, spaceAfter=3))] if title else []
    content.append(Paragraph(text, ParagraphStyle("bx", parent=body, spaceAfter=0)))
    t = Table([[content]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return [t, Spacer(1, 8)]


def steps(items):
    return [Paragraph(f"<b>{i}.</b>&nbsp;&nbsp;{s}", step) for i, s in enumerate(items, 1)]


def table(rows, widths, header=True):
    data = [[Paragraph(c, cellb if (header and r == 0) else cell) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
          ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if header: st.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(st))
    return [t, Spacer(1, 10)]


def cover(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(DARK); c.rect(0, 0, w, h, stroke=0, fill=1)
    # grid lines, like the panel's background
    c.setStrokeColor(colors.HexColor("#1e293b")); c.setLineWidth(0.4)
    for x in range(0, int(w), 28): c.line(x, 0, x, h * 0.42)
    for y in range(0, int(h * 0.42), 28): c.line(0, y, w, y)
    c.setFillColor(NEON); c.rect(22 * mm, h - 62 * mm, 14 * mm, 2.2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Sans-B", 34); c.drawString(22 * mm, h - 80 * mm, "PhoneBox")
    c.setFillColor(NEON); c.setFont("Sans-B", 16); c.drawString(22 * mm, h - 92 * mm, "Manuel d'installation")
    c.setFillColor(colors.HexColor("#cbd5e1")); c.setFont("Sans", 11.5)
    for i, line in enumerate(["Un ancien téléphone Android devient le tableau de commande du PC :",
                              "Teams, Outlook, Console Admin, suivi des sites, musique et raccourcis,",
                              "reliés en Bluetooth, sans port réseau ni règle de pare-feu."]):
        c.drawString(22 * mm, h - 108 * mm - i * 6.5 * mm, line)
    # phone silhouette
    px, py, pw, ph = w - 78 * mm, h * 0.42 + 6 * mm, 52 * mm, 30 * mm
    c.setFillColor(colors.HexColor("#111827")); c.setStrokeColor(colors.HexColor("#334155")); c.setLineWidth(1.2)
    c.roundRect(px, py, pw, ph, 4 * mm, stroke=1, fill=1)
    tiles = [("#22c55e", "Micro"), ("#6264a7", "Teams"), ("#0078d4", "Outlook"), ("#ef4444", "Verrou"), ("#a3e635", "Sites"), ("#f59e0b", "Musique")]
    for i, (col, label) in enumerate(tiles):
        tx = px + 4 * mm + (i % 3) * 15.3 * mm; ty = py + ph - 13 * mm - (i // 3) * 11 * mm
        c.setFillColor(colors.HexColor("#1f2937")); c.setStrokeColor(colors.HexColor(col)); c.setLineWidth(0.9)
        c.roundRect(tx, ty, 13.5 * mm, 9 * mm, 1.6 * mm, stroke=1, fill=1)
        c.setFillColor(colors.HexColor(col)); c.setFont("Sans-B", 6.2); c.drawCentredString(tx + 6.75 * mm, ty + 3.4 * mm, label)
    c.setFillColor(colors.HexColor("#94a3b8")); c.setFont("Sans", 9)
    c.drawString(22 * mm, 30 * mm, "Édition Bluetooth  ·  Windows 11 64 bits  ·  Android 5 ou plus")
    c.drawString(22 * mm, 24 * mm, "Support informatique  ·  novembre 2026  ·  à partir du projet libre PhoneBox (licence MIT)")
    c.restoreState()


def page(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(NEON); c.rect(20 * mm, h - 14 * mm, 8 * mm, 1.4 * mm, stroke=0, fill=1)
    c.setFillColor(MUTED); c.setFont("Sans", 8.5)
    c.drawString(31 * mm, h - 14.4 * mm, "PhoneBox  ·  Manuel d'installation")
    c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(20 * mm, 14 * mm, w - 20 * mm, 14 * mm)
    c.drawString(20 * mm, 9 * mm, "Document interne  ·  Support informatique")
    c.drawRightString(w - 20 * mm, 9 * mm, f"Page {doc.page}")
    c.restoreState()


doc = BaseDocTemplate("/home/claude/manuel/out/Manuel d'installation PhoneBox.pdf", pagesize=A4,
                      title="PhoneBox - Manuel d'installation", author="Support informatique", subject="Installation du deck PhoneBox (Bluetooth)",
                      leftMargin=20 * mm, rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=20 * mm)
fr = Frame(20 * mm, 20 * mm, 170 * mm, 255 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="cover", frames=[fr], onPage=cover), PageTemplate(id="page", frames=[fr], onPage=page)])

S = [NextPageTemplate("page"), PageBreak()]

# ---------------- 1
S += [Paragraph("1. En bref", h1),
      Paragraph("PhoneBox transforme un téléphone Android en écran de commande posé à côté du PC : boutons Teams, "
                "agenda Outlook, ouverture directe des modules de la Console Admin, état des sites suivis, verrouillage "
                "du poste, musique… Le téléphone et le PC communiquent <b>en Bluetooth</b>.", body)]
S += table([["Élément", "Rôle"],
            ["<b>PhoneBoxAgent.exe</b> (PC)", "Petit programme qui tourne avec votre compte Windows, sans droits administrateur. Il exécute les boutons et fournit les informations affichées."],
            ["<b>Appli PhoneBox</b> (téléphone)", "Affiche le tableau de commande. Elle n'envoie que le numéro du bouton touché, jamais une commande."],
            ["<b>Liaison Bluetooth</b>", "Le PC se connecte lui-même au téléphone appairé. Aucun port n'est ouvert sur le réseau et aucune règle de pare-feu n'est nécessaire."]],
           [50, 120])
S += box("Les commandes, mots de passe, jetons et adresses restent sur le PC. Les échanges sont chiffrés deux fois "
         "(Bluetooth, puis TLS avec certificat épinglé) et seul un téléphone appairé par QR code peut utiliser le PC.",
         title="Sécurité")

# ---------------- 2
S += [Paragraph("2. Prérequis", h2)]
S += table([["PC", "Téléphone"],
            ["Windows 10 ou 11, <b>64 bits</b><br/>Bluetooth présent et activé<br/>Outlook classique (pour l'agenda et les non-lus)",
             "Android 5 ou plus récent, avec Bluetooth<br/>Un câble USB pour le garder chargé<br/>Mode développeur <b>inutile</b>"]],
           [85, 85])

# ---------------- 3
S += [Paragraph("3. Téléchargements", h2),
      Paragraph("Les liens pointent toujours vers la dernière version. Aucun compte GitHub n'est nécessaire.", body)]
S += table([["Fichier", "Lien direct"],
            ["Agent pour le PC (zip)", link(ZIP, "PhoneBox-Bluetooth-Windows.zip")],
            ["Appli pour le téléphone", link(APK, "PhoneBox-Bluetooth.apk")],
            ["Page de la version", link(PAGE, "Notes et fichiers de la dernière version")]],
           [55, 115])
S += [Paragraph("Adresses complètes, pour les recopier :", small),
      Paragraph(ZIP, code), Paragraph(APK, code)]

# ---------------- 4
S += [PageBreak(), Paragraph("4. Installer l'agent sur le PC", h1)]
S += steps(["Téléchargez <b>PhoneBox-Bluetooth-Windows.zip</b>.",
            "Créez un dossier vide <b>Documents\\PhoneBox</b>, puis clic droit sur le zip → <b>Extraire tout</b> vers ce dossier. "
            "Évitez le Bureau synchronisé OneDrive, Program Files et la racine de C:.",
            "Double-cliquez sur <b>PhoneBoxAgent.exe</b>. Si Windows affiche « Windows a protégé votre ordinateur » : "
            "<b>Informations complémentaires</b> → <b>Exécuter quand même</b>.",
            "Une icône PhoneBox apparaît près de l'horloge et la page des réglages s'ouvre dans le navigateur "
            "(adresse : <b>http://127.0.0.1:8765</b>)."])
S += box("Gardez le dossier <b>Scripts</b> à côté de PhoneBoxAgent.exe : la page Bureau (chapitre 8) l'utilise.",
         title="Bon à savoir")
S += [Paragraph("Mise à jour", h2),
      Paragraph("Quittez PhoneBox (clic droit sur l'icône → Quitter, ou Gestionnaire des tâches → PhoneBoxAgent → Fin de tâche), "
                "extrayez le nouveau zip au même endroit en remplaçant les fichiers, puis relancez PhoneBoxAgent.exe. "
                "Vos réglages sont conservés.", body)]

# ---------------- 5
S += [Paragraph("5. Installer l'appli sur le téléphone", h1)]
S += steps(["Sur le téléphone, ouvrez le lien de <b>PhoneBox-Bluetooth.apk</b> (chapitre 3).",
            "Ouvrez le fichier téléchargé. Si Android le demande, autorisez votre navigateur à installer des applications.",
            "Si une ancienne appli PhoneBox (version d'origine, téléchargée ailleurs) est installée, <b>désinstallez-la d'abord</b> : Android refuse sinon la nouvelle. "
            "Une mise à jour de PhoneBox, elle, s'installe par-dessus.",
            "Ouvrez l'appli. À la question <b>Appareils à proximité</b>, répondez <b>Autoriser</b> : c'est l'accès Bluetooth."])

# ---------------- 6
S += [PageBreak(), Paragraph("6. Appairer le téléphone et le PC en Bluetooth", h1),
      Paragraph("À faire une seule fois, comme pour un casque.", body)]
S += steps(["Sur le téléphone : <b>Paramètres → Connexions → Bluetooth</b>, et restez sur cet écran (le téléphone n'est visible que tant qu'il est ouvert).",
            "Sur le PC : <b>Paramètres → Bluetooth et appareils → Ajouter un appareil → Bluetooth</b>. "
            "Si le téléphone n'apparaît pas, réglez <b>Détection des appareils Bluetooth</b> sur <b>Avancé</b>.",
            "Choisissez le téléphone et vérifiez que le <b>même code à 6 chiffres</b> s'affiche des deux côtés, puis confirmez.",
            "Windows indique ensuite « Appairé » ou « Non connecté » : <b>c'est normal</b>. PhoneBox établit la connexion lui-même."])
S += box("En cas d'échec, supprimez l'ancien appairage des deux côtés (PC : Supprimer l'appareil ; téléphone : Dissocier), "
         "coupez puis rallumez le Bluetooth et recommencez. Fermez aussi « Mobile connecté / Lien avec Windows » s'il est ouvert.",
         bg=WARN_BG, edge=WARN, title="Si l'appairage échoue")

# ---------------- 7
S += [Paragraph("7. Associer PhoneBox (QR code)", h1),
      Paragraph("Cette étape donne au téléphone la clé du PC. <b>L'ordre compte</b> : l'appli doit être ouverte avant de scanner.", body)]
S += steps(["Ouvrez l'appli PhoneBox sur le téléphone et attendez <b>environ 20 secondes</b> : le PC la trouve en Bluetooth.",
            "Sur le PC, dans les réglages PhoneBox : <b>Général → Wi-Fi et Tailscale → Associer un téléphone</b>. Un QR code s'affiche.",
            "Scannez-le avec l'appareil photo du téléphone, puis touchez <b>Ouvrir dans PhoneBox</b> sur la page qui s'affiche.",
            "Vérifiez que le code de contrôle affiché sur le téléphone est le même que celui du PC, puis validez. Le tableau de commande apparaît."])
S += box("Pour vérifier que le PC voit le téléphone, ouvrez <b>http://127.0.0.1:8765/api/bluetooth</b> sur le PC : "
         "« connected » et le nom du téléphone doivent s'afficher.", title="Contrôle rapide")
S += box("Un même téléphone peut être associé à plusieurs PC (bureau et domicile). Il affiche automatiquement "
         "le tableau du PC qui s'y connecte.", title="Plusieurs PC")

# ---------------- 8
S += [PageBreak(), Paragraph("8. Le tableau de commande", h1),
      Paragraph("Au premier lancement, l'agent prépare tout seul une page <b>Bureau</b>, affichée en premier sur le téléphone :", body)]
S += table([["Dalle", "Ce qu'elle fait / ce qu'il reste à faire"],
            ["Prochain rendez-vous", "Votre prochaine réunion Outlook. Le calendrier d'Outlook classique est ajouté automatiquement s'il est installé ; rien ne quitte le PC."],
            ["Teams", "Micro, caméra, main levée, partage, quitter. Le micro fonctionne même si Teams est en arrière-plan ; les autres boutons mettent Teams au premier plan avant d'agir."],
            ["Verrouillage", "Verrouiller le poste ou éteindre les écrans."],
            ["Mes sites", "État des routeurs (.254) de vos sites : vert = répond, rouge = hors ligne. <b>À faire :</b> listez vos villes dans <b>Mes-sites.txt</b> (dossier Scripts), une par ligne, comme dans la matrice de la Console Admin. Le fichier est créé au premier passage."],
            ["Wrike", "Vos tâches Wrike clôturées aujourd'hui. <b>À faire une fois :</b> enregistrer votre jeton Wrike (ci-dessous)."],
            ["Mails non lus", "Nombre de messages non lus d'Outlook classique, sans ouvrir aucun message. Outlook doit être ouvert."],
            ["Musique du téléphone", "La musique jouée sur le téléphone (Deezer, Spotify…). Au premier usage, touchez <b>Autoriser l'accès</b> et activez PhoneBox dans l'accès aux notifications."]],
           [40, 130])
S += [Paragraph("Enregistrer le jeton Wrike (une seule fois)", h2)]
S += steps(["Dans Wrike : <b>photo de profil → Applications et intégrations → API</b>, nommez l'application (par exemple « Deck »), "
            "puis <b>Jeton d'accès permanent → Créer un jeton</b>. Copiez-le : il n'est affiché qu'une fois.",
            "Ouvrez le dossier <b>Scripts</b> de PhoneBox, cliquez dans la barre d'adresse de l'explorateur, tapez <b>powershell</b> et appuyez sur Entrée.",
            "Dans la fenêtre bleue, tapez ces deux lignes (Entrée après chacune) :"])
S += [Paragraph("Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force<br/>.\\Wrike-Taches-du-jour.ps1 -Configurer", code)]
S += [Paragraph("<b>4.</b>&nbsp;&nbsp;Collez le jeton quand il est demandé (clic droit ; rien ne s'affiche, c'est normal), Entrée, puis Entrée pour l'adresse. "
                "« Jeton enregistré. » confirme. Le jeton est chiffré avec votre compte Windows et ne va jamais sur le téléphone.", step)]
S += box("Ne collez jamais le jeton ailleurs que dans cette fenêtre (mail, chat…). S'il a été exposé, supprimez-le dans Wrike et créez-en un autre.",
         bg=WARN_BG, edge=WARN, title="Confidentialité")
S += [Paragraph("Ajouter ou modifier des dalles", h2),
      Paragraph("Dans les réglages (icône PhoneBox → Paramètres), ouvrez une page, ajoutez un widget depuis la liste et glissez-le dans la grille. "
                "Pour une dalle de script, choisissez le widget <b>Commande</b> et indiquez par exemple :", body),
      Paragraph('&amp; "$env:PHONEBOX_DIR\\Scripts\\Suivi-Sites.ps1"', code),
      Paragraph("<b>$env:PHONEBOX_DIR</b> désigne le dossier où PhoneBox est installé : la même ligne fonctionne sur tous les postes.", small)]
S += [Paragraph("Console Admin", h2),
      Paragraph("Créez un <b>gros bouton</b> (ou un raccourci) avec la commande :", body),
      Paragraph('wscript.exe "...\\Console-Admin_V4.5\\Lancer Console Admin.vbs" Ordinateurs', code),
      Paragraph("Le module s'ouvre juste après la connexion, avec les droits du compte. Modules possibles : Accueil, Utilisateur, "
                "Annuaire, Purge, Ordinateurs (ou LAPS, BitLocker), Ping, Cartographie, Secteurs, Telephonie, Journal, Parametrage. "
                "Sans nom de module, la console s'ouvre normalement. Nécessite la version de la Console Admin qui gère l'option -Module.", body)]

# ---------------- 9
S += [PageBreak(), Paragraph("9. Option : quotas Claude", h1),
      Paragraph("Le widget <b>Quotas IA</b> affiche la consommation d'un forfait Claude Pro ou Max (limite de 5 heures et limite hebdomadaire, "
                "communes à Claude et Claude Code). Il s'appuie sur la connexion de <b>Claude Code</b>, qu'il faut installer une fois.", body)]
S += steps(["Ouvrez <b>Windows PowerShell</b> (pas la version « x86 », sinon l'installation croit Windows en 32 bits).",
            "Lancez l'installation, puis fermez et rouvrez PowerShell :"])
S += [Paragraph("irm https://claude.ai/install.ps1 | iex", code)]
S += steps(["Tapez <b>claude</b> et connectez-vous dans le navigateur avec votre compte Pro ou Max.",
            "Relancez PhoneBoxAgent : le widget se remplit dans la minute."])
S += [Paragraph("Documentation officielle : " + link(CLAUDE_DOC), small), Spacer(1, 4)]
S += box("Le widget <b>Sessions IA</b> n'affiche que les sessions ouvertes dans Claude Code, pas les conversations claude.ai. "
         "Vérifiez que l'installation de Claude Code est autorisée sur votre poste.", bg=WARN_BG, edge=WARN, title="À noter")

# ---------------- 10
S += [PageBreak(), Paragraph("10. Dépannage", h1)]
S += table([["Symptôme", "Solution"],
            ["« PC non connecté » sur le téléphone", "Vérifiez que l'agent tourne (icône près de l'horloge) et que le Bluetooth est actif des deux côtés. "
             "Gardez l'appli ouverte 20 secondes. Contrôle : http://127.0.0.1:8765/api/bluetooth."],
            ["« Ce lien d'appariement est incomplet »", "L'agent ou l'appli n'est pas à jour : réinstallez les deux, puis générez un nouveau QR code."],
            ["« L'appairage n'a pas fonctionné »", "L'appli n'était pas encore reliée au PC : ouvrez-la, attendez 20 secondes, puis rescannez."],
            ["L'installation de l'appli est refusée", "Désinstallez l'ancienne appli PhoneBox d'origine. Sur un téléphone géré par l'entreprise, l'installation hors Play Store peut être bloquée."],
            ["« Accès refusé » à l'extraction du zip", "Arrêtez PhoneBoxAgent dans le Gestionnaire des tâches, extrayez dans un dossier vide ; "
             "au besoin, clic droit sur le zip → Propriétés → Débloquer."],
            ["Boutons Teams sans effet", "Teams doit être ouvert et en réunion. Le micro utilise Win+Alt+K ; les autres boutons mettent Teams au premier plan."],
            ["Dalle de script vide ou en erreur", "Vérifiez que le dossier <b>Scripts</b> est bien à côté de PhoneBoxAgent.exe. Pour voir le message exact, ouvrez PowerShell dans le dossier Scripts et lancez le script (voir chapitre 8)."],
            ["Agenda vide", "Outlook classique requis (pas le nouvel Outlook ni Outlook sur le web) ; vérifiez le calendrier « Outlook » dans les réglages."],
            ["Musique du téléphone : « Autoriser l'accès »", "Activez PhoneBox dans Paramètres → Notifications → Accès aux notifications."],
            ["Installation de Claude Code : « 32-bit Windows »", "Vous êtes dans PowerShell (x86) : ouvrez « Windows PowerShell » 64 bits."]],
           [58, 112])

# ---------------- 11
S += [Paragraph("11. Désinstaller", h2),
      Paragraph("PC : quittez PhoneBox et supprimez le dossier PhoneBox (les réglages sont dans %APPDATA%\\PhoneBox). "
                "Téléphone : désinstallez l'appli, retirez l'appairage Bluetooth et, si vous l'aviez accordé, l'accès aux notifications.", body)]

doc.build(S)
print("ok")
