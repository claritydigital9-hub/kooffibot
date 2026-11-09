# -*- coding: utf-8 -*-
import os, json, requests, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from google import genai
from google.genai import types

# 1. CONFIGURATION META & GEMINI
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAAWhxl1ur38BSzCOugMGBybAW0rA7JarcTONY6kPB1GqOu3fnSsfoyqparDXutHbgBfZCoWqSKxZCYp7rI0OdUV7T6ldFrdif69rb2ptJzZCZAbBibzafJ8s0zLBpBM0peRWtmZBa1ruJpR7X1b8Qeke0TF2mkmrnp2XO0WiHVbHO1Vs917WyKLNn7dAELVaUNgZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "1244852872055806")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mon_token_secret_koffi")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IkgJIlIqDHEl1T4HzCZfcw6H3n1rOcq1IUOYBsQGAKnA")

# Numéros Administrateurs Clarity Digital (Alexis)
NUMEROS_ADMIN = ["22893092692", "22897633742"]
NUMERO_CHEF = os.environ.get("NUMERO_CHEF", "22897633742")

# URL de l'affiche officielle du menu sur GitHub public
MENU_IMAGE_URL = os.environ.get(
    "MENU_IMAGE_URL", 
    "https://raw.githubusercontent.com/claritydigital9-hub/kooffibot/main/Code_Generated_Image.png"
)

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
messages_traites = set()
FICHIER_MEMOIRE = "memoires_clients.json"
FICHIER_RESERVATIONS = "reservations.json"

# 2. PERSISTANCE SUR DISQUE (ZÉRO AMNÉSIE)
def charger_memoires():
    if os.path.exists(FICHIER_MEMOIRE):
        try:
            with open(FICHIER_MEMOIRE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception: return {}
    return {}

def sauvegarder_memoires():
    try:
        with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
            json.dump(memoires_clients, f, ensure_ascii=False, indent=2)
    except Exception: pass

def enregistrer_reservation_fichier(details):
    try:
        historique = []
        if os.path.exists(FICHIER_RESERVATIONS):
            with open(FICHIER_RESERVATIONS, "r", encoding="utf-8") as f:
                historique = json.load(f)
        historique.append(details)
        with open(FICHIER_RESERVATIONS, "w", encoding="utf-8") as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] Erreur log réservation : {e}")

memoires_clients = charger_memoires()

# 3. ENVOIS VIA META GRAPH API
def envoyer_message_texte(to_phone, texte):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": texte}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[✓] Message envoyé vers {to_phone} : {r.status_code}")
    except Exception as e:
        print(f"[!] Erreur envoi texte : {e}")

def envoyer_photo_menu(to_phone):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "image",
        "image": {
            "link": MENU_IMAGE_URL,
            "caption": "Voici notre carte officielle Le Braisé Lounge avec tous nos tarifs en F CFA !"
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[✓] Photo menu envoyée vers {to_phone} : {r.status_code}")
    except Exception as e:
        print(f"[!] Erreur photo : {e}")

def notifier_chef(nom, heure, couverts, plats, tel_client):
    texte_alerte = (
        f"🔔 *NOUVELLE RÉSERVATION VALIDÉE !*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Client :* {nom}\n"
        f"👥 *Couverts :* {couverts}\n"
        f"⏰ *Heure d'arrivée :* {heure}\n"
        f"🍗 *Plats :* {plats}\n"
        f"📞 *WhatsApp Client :* +{tel_client}\n"
        f"📅 *Date :* {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Table réservée automatiquement par Koffi."
    )
    print(f"\n[!] ALERTE CHEF ENVOYÉE AU {NUMERO_CHEF} pour {nom}")
    envoyer_message_texte(NUMERO_CHEF, texte_alerte)
    
    enregistrer_reservation_fichier({
        "nom": nom,
        "heure": heure,
        "couverts": couverts,
        "plats": plats,
        "telephone": tel_client,
        "date": datetime.now().isoformat()
    })

# 4. MODULE CLARITYHUNTER : PROSPECTION ET VEILLE COMMERCIALE EN DIRECT
def executer_chasse_prospects(requete, to_phone):
    envoyer_message_texte(
        to_phone, 
        f"🔎 *ClarityHunter activé !*\n"
        f"Je recherche et analyse des cibles à Lomé pour : \"{requete}\"...\n"
        f"Traitement en cours, votre rapport complet arrive dans quelques secondes."
    )

    prompt_hunter = f"""Tu es ClarityHunter, l'agent d'intelligence commerciale et de prospection B2B de l'agence Clarity Digital à Lomé (Togo).
Fondateur : Alexis Karim Koubadjè.

Demande de prospection : "{requete}" à Lomé (Togo).

MISSION :
Fournis une sélection de 3 à 5 vraies entreprises cibles à Lomé dans ce secteur.
Pour chaque entreprise, présente obligatoirement :
1. 🏢 Nom de l'établissement & Quartier précis à Lomé (ex: Agoè, Tokoin, Déckon, Adidogomé, Avedji, Bè...).
2. 📞 Contact téléphonique / WhatsApp direct (+228...).
3. 🎯 Opportunité commerciale détectée (ce que les clients disent, faiblesses, besoin d'un agent IA WhatsApp de réservation ou de vidéos).
4. 💬 Message d'accroche WhatsApp sur-mesure prêt à copier-coller (court, percutant, mentionnant leur quartier et proposant une démo en direct sur le +1 555-632-3537).

Termine par un court conseil stratégique de closing pour Alexis.
Reste très clair, bien espacé avec des émojis pour une lecture facile sur smartphone WhatsApp."""

    modeles_hunter = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    rapport_genere = None
    for mh in modeles_hunter:
        try:
            resp = client_gemini.models.generate_content(
                model=mh,
                contents=prompt_hunter,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=1200
                )
            )
            if resp and resp.text:
                rapport_genere = resp.text.strip()
                break
        except Exception:
            continue

    if rapport_genere:
        rapport = f"🎯 *RAPPORT CLARITYHUNTER — PROSPECTION LOMÉ*\n━━━━━━━━━━━━━━━━━━━\n\n" + rapport_genere
        if len(rapport) > 3500:
            parties = [rapport[i:i+3000] for i in range(0, len(rapport), 3000)]
            for p in parties:
                envoyer_message_texte(to_phone, p)
        else:
            envoyer_message_texte(to_phone, rapport)
    else:
        envoyer_message_texte(to_phone, "❌ Erreur temporaire lors de la recherche. Veuillez reformuler votre demande (ex: Chasse: 5 restaurants à Lomé).")

# 5. MODULE RESTAURANT : KOFFI (FLUIDITÉ TOTALE & ZÉRO RÉPÉTITION)
def generer_reponse_koffi(from_phone, text_client):
    deja_salue = False
    historique_existant = memoires_clients.get(from_phone, [])
    for msg in historique_existant:
        if msg.startswith("Koffi:"):
            deja_salue = True
            break

    h = datetime.now().hour
    salutation_moment = "Bonjour" if 5 <= h < 14 else "Bonsoir"

    consigne_salutation = (
        "⚠️ CONVERSATION DÉJÀ EN COURS : Ne dis JAMAIS 'Bonjour' ni 'Bonsoir' ! Enchaîne directement avec enthousiasme (ex: 'Avec plaisir !', 'C'est bien noté !', 'Parfait !')."
        if deja_salue else
        f"C'est le tout premier message : Salue chaleureusement avec '{salutation_moment}' et souhaite la bienvenue."
    )

    prompt_systeme = f"""Tu es Koffi, le maître d'hôtel chaleureux, poli et dynamique du restaurant "Le Braisé Lounge & Saveurs d'Ivoire" à Adidogomé (Lomé, Togo).
Ton but est de converser comme un vrai serveur togolais expérimenté sur WhatsApp.

INFORMATIONS DU RESTAURANT :
- Localisation : Lomé, quartier Adidogomé, non loin du grand carrefour / boulevard principal.
- Lien Google Maps : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome
- Téléphone direct : +228 90 00 00 00
- Carte & Prix :
  * Poulet braisé entier : 7.000 F CFA | Demi-poulet : 4.000 F CFA
  * Poissons braisés frais (Carpe / Bar) : 5.000 F à 10.000 F CFA selon la taille
  * Brochettes de bœuf assaisonnées : 3.000 F CFA la portion
  * Garba au thon rouge : 1.500 F à 3.000 F CFA
  * Accompagnements : Alloco (1.000 F), Frites, Attiéké

RÈGLES D'OR DE DIALOGUE HUMAIN :
1. {consigne_salutation}
2. NE PAS RÉPÉTER LE NOM : N'utilise pas le nom du client dans chaque phrase. Utilise-le avec parcimonie et naturel.
3. ENVOI DE CARTE / PHOTO : Si le client demande la carte en photo, confirme avec joie que tu lui envoies tout de suite. N'écris JAMAIS dans ton texte de parenthèses ou de descriptions d'actions comme "(Photo de la carte...)".
4. PRÉSENTATION DES PLATS : Quand le client demande ce qu'il y a à manger, cite les spécialités avec leurs prix en F CFA en donnant envie.
5. VALIDATION STRICTE DE RÉSERVATION :
   Dès que tu as le Nom, l'Heure et le Nombre de personnes :
   - Confirme chaleureusement la table.
   - Propose d'anticiper la cuisson d'un plat si ce n'est pas encore fait.
   - Ajoute STRICTEMENT à la fin de ta réponse cette balise invisible :
   [RESERVATION: Nom=... | Heure=... | Couverts=... | Plats=...]"""

    historique = historique_existant[-10:]
    dialogue_str = "\n".join(historique)
    contenu_final = f"""Historique de notre conversation :\n{dialogue_str}\n\nClient: {text_client}\n\nRéponse de Koffi :"""

    modeles = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    for m in modeles:
        try:
            resp = client_gemini.models.generate_content(
                model=m,
                contents=contenu_final,
                config=types.GenerateContentConfig(
                    system_instruction=prompt_systeme,
                    temperature=0.6,
                    max_output_tokens=350
                )
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception:
            continue

    if "maps" in text_client.lower() or "localisation" in text_client.lower():
        return "Voici notre emplacement exact sur Google Maps à Adidogomé : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome . Nous vous y attendons avec plaisir !"
    return "C'est bien noté ! C'est parfaitement enregistré pour vous au Braisé Lounge. Que puis-je vous préparer d'autre ?"

# 6. GESTION DU WEBHOOK ET AIGUILLAGE INTELLIGENT
def traiter_webhook_async(body_str):
    try:
        data = json.loads(body_str)
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        val = changes.get('value', {})
        messages = val.get('messages', [])
        if not messages: return

        msg = messages[0]
        msg_id = msg.get('id')
        from_phone = msg.get('from', '')
        text_client = msg.get('text', {}).get('body', '').strip()

        if not text_client or not msg_id: return
        if msg_id in messages_traites: return
        messages_traites.add(msg_id)
        if len(messages_traites) > 500: messages_traites.clear()

        print(f"\n[+] Message reçu de {from_phone} : {text_client}")

        # --- AIGUILLAGE 1 : COMMANDE ADMIN DE PROSPECTION (CLARITYHUNTER) ---
        match_chasse = re.match(r'^(chasse|prospect|recherche|veille)\s*[:=]\s*(.+)$', text_client, re.IGNORECASE)
        if match_chasse and any(admin in from_phone for admin in NUMEROS_ADMIN):
            requete = match_chasse.group(2).strip()
            print(f"[🔥] COMMANDE ADMIN DÉTECTÉE de {from_phone} : {requete}")
            threading.Thread(target=executer_chasse_prospects, args=(requete, from_phone)).start()
            return

        # --- AIGUILLAGE 2 : CONVERSATION RESTAURANT KOFFI ---
        if from_phone not in memoires_clients:
            memoires_clients[from_phone] = []
        memoires_clients[from_phone].append(f"Client: {text_client}")

        reponse_brute = generer_reponse_koffi(from_phone, text_client)

        reponse_client = reponse_brute
        match = re.search(r'\[RESERVATION[^\]]*Nom\s*[:=]\s*([^\|\]]+)[^\]]*Heure\s*[:=]\s*([^\|\]]+)[^\]]*Couverts\s*[:=]\s*([^\|\]]+)(?:[^\]]*Plats\s*[:=]\s*([^\|\]]+))?[^\]]*\]', reponse_brute, re.IGNORECASE)
        if match:
            nom_c = match.group(1).strip()
            heure_c = match.group(2).strip()
            couverts_c = match.group(3).strip()
            plats_c = match.group(4).strip() if match.group(4) else "Non spécifiés"
            reponse_client = re.sub(r'\[RESERVATION.*?\]', '', reponse_brute, flags=re.IGNORECASE).strip()
            threading.Thread(target=notifier_chef, args=(nom_c, heure_c, couverts_c, plats_c, from_phone)).start()
        elif "officiellement réservée" in reponse_brute.lower() or "table est réservée" in reponse_brute.lower():
            threading.Thread(target=notifier_chef, args=("Client", "Confirmé", "Réservé", "Voir échange", from_phone)).start()

        memoires_clients[from_phone].append(f"Koffi: {reponse_client}")
        sauvegarder_memoires()

        print(f"[>] Koffi répond : {reponse_client}")
        envoyer_message_texte(from_phone, reponse_client)

        mots_menu = ["carte", "menu", "photo", "visuel", "flyer"]
        if any(mot in text_client.lower() for mot in mots_menu):
            envoyer_photo_menu(from_phone)

    except Exception as e:
        print(f"[!] Erreur webhook : {e}")

class WhatsAppHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        mode = query.get('hub.mode', [None])[0]
        token = query.get('hub.verify_token', [None])[0]
        challenge = query.get('hub.challenge', [None])[0]

        if mode == 'subscribe' and token == VERIFY_TOKEN:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(challenge.encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"SERVEUR HYBRIDE KOFFI + CLARITYHUNTER ACTIF SUR RENDER 24/7")

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8')
        threading.Thread(target=traiter_webhook_async, args=(body,)).start()

def run():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), WhatsAppHandler)
    print(f"[*] Serveur Hybride Koffi + ClarityHunter en écoute 24/7 sur le port {port}...")
    server.serve_forever()

if __name__ == '__main__':
    run()
