# -*- coding: utf-8 -*-
import os, json, requests, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from google import genai
from google.genai import types

# 1. CONFIGURATION META & GOOGLE GEMINI
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAAWhxl1ur38BSzCOugMGBybAW0rA7JarcTONY6kPB1GqOu3fnSsfoyqparDXutHbgBfZCoWqSKxZCYp7rI0OdUV7T6ldFrdif69rb2ptJzZCZAbBibzafJ8s0zLBpBM0peRWtmZBa1ruJpR7X1b8Qeke0TF2mkmrnp2XO0WiHVbHO1Vs917WyKLNn7dAELVaUNgZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "1244852872055806")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mon_token_secret_koffi")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IkgJIlIqDHEl1T4HzCZfcw6H3n1rOcq1IUOYBsQGAKnA")

# Numéro du Chef / Gérant qui reçoit les réservations (ton numéro)
NUMERO_CHEF = os.environ.get("NUMERO_CHEF", "22893092692")

# URL OFFICIELLE DE TON AFFICHE MENU HÉBERGÉE SUR GITHUB
MENU_IMAGE_URL = os.environ.get(
    "MENU_IMAGE_URL", 
    "https://raw.githubusercontent.com/claritydigital9-hub/kooffibot/main/Code_Generated_Image.png"
)

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
messages_traites = set()
FICHIER_MEMOIRE = "memoires_clients.json"
FICHIER_RESERVATIONS = "reservations.json"

# 2. PERSISTANCE DE LA MÉMOIRE (ZÉRO PERTE AU REDÉMARRAGE)
def charger_memoires():
    if os.path.exists(FICHIER_MEMOIRE):
        try:
            with open(FICHIER_MEMOIRE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def sauvegarder_memoires():
    try:
        with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
            json.dump(memoires_clients, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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
        print(f"[!] Erreur sauvegarde réservation : {e}")

memoires_clients = charger_memoires()

# 3. ENVOIS VIA WHATSAPP GRAPH API
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
        print(f"[✓] Texte envoyé vers {to_phone} : {r.status_code}")
    except Exception as e:
        print(f"[!] Erreur texte : {e}")

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
        f"Table enregistrée automatiquement par Koffi."
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

# 4. CERVEAU DE KOFFI (PROMPT PERFECTIONNÉ SANS PARENTHÈSES)
def generer_reponse_koffi(from_phone, text_client):
    texte_lower = text_client.lower()
    if "bonsoir" in texte_lower:
        salutation = "Bonsoir"
    elif "bonjour" in texte_lower:
        salutation = "Bonjour"
    else:
        h = datetime.now().hour
        salutation = "Bonjour" if 5 <= h < 14 else "Bonsoir"

    prompt_systeme = f"""Tu es Koffi, le maître d'hôtel chaleureux, poli et très professionnel du restaurant "Le Braisé Lounge & Saveurs d'Ivoire" à Adidogomé (Lomé, Togo).
Ton but est de converser naturellement comme un être humain sur WhatsApp.

INFORMATIONS DU RESTAURANT :
- Localisation : Lomé, quartier Adidogomé, non loin du grand carrefour / boulevard principal.
- Lien Google Maps officiel : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome
- Téléphone direct / Infoline : +228 90 00 00 00
- Présence en ligne : TikTok (@lebraiselounge) et Instagram !
- Carte & Prix :
  * Poulet braisé entier : 7.000 F CFA | Demi-poulet : 4.000 F CFA
  * Poissons braisés frais (Carpe / Bar) : 5.000 F à 10.000 F CFA selon la taille
  * Brochettes de bœuf assaisonnées : 3.000 F CFA la portion
  * Garba au thon rouge : 1.500 F à 3.000 F CFA
  * Accompagnements : Alloco (1.000 F), Frites, Attiéké

RÈGLES D'OR DE CONVERSATION :
1. MÉMOIRE DU CLIENT : Retiens toujours son nom (ex: "chef Lefa") et utilise-le avec respect tout au long de la discussion.
2. ENVOI DE CARTE / PHOTO : Si le client demande la carte ou le menu en photo, confirme-lui avec enthousiasme que tu lui envoies la carte tout de suite.
   ⚠️ INTERDICTION STRICTE : N'écris JAMAIS dans ton texte de parenthèses ou de descriptions d'actions comme "(Photo de la carte...)" ou "[Photo envoyée]". Contente-toi d'écrire un message chaleureux.
3. PRÉSENTATION DES PLATS : Quand le client demande ce qu'il y a à manger, cite toujours les plats accompagnés de leurs prix en F CFA avec gourmandise.
4. VALIDATION STRICTE DE LA RÉSERVATION :
   Dès que tu as le Nom, l'Heure et le Nombre de personnes :
   - Confirme chaleureusement la table.
   - Si le client n'a pas encore choisi ses plats, propose-lui gentiment de commander à l'avance pour que la cuisine commence à griller avant son arrivée !
   - Ajoute STRICTEMENT à la fin de ta réponse cette balise invisible :
   [RESERVATION_CONFIRMEE: Nom=... | Heure=... | Couverts=... | Plats=...]
5. Salutation actuelle : Réponds avec "{salutation}" si tu dois saluer."""

    historique = memoires_clients.get(from_phone, [])[-12:]
    dialogue_str = "\n".join(historique)
    
    contenu_final = f"""Historique de notre conversation :
{dialogue_str}

Client: {text_client}

Réponse de Koffi :"""

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

    if "maps" in texte_lower or "localisation" in texte_lower:
        return "Voici notre emplacement exact sur Google Maps à Adidogomé : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome . Nous vous y attendons avec plaisir !"
    return "C'est bien noté chef ! C'est parfaitement enregistré pour vous au Braisé Lounge. Que puis-je vous préparer d'autre ?"

# 5. TRAITEMENT ASYNCHRONE DES MESSAGES ENTRANTS
def traiter_webhook_async(body_str):
    try:
        data = json.loads(body_str)
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        val = changes.get('value', {})
        messages = val.get('messages', [])
        if not messages:
            return

        msg = messages[0]
        msg_id = msg.get('id')
        from_phone = msg.get('from')
        text_client = msg.get('text', {}).get('body', '').strip()

        if not text_client or not msg_id:
            return

        # Protection anti-doublons
        if msg_id in messages_traites:
            return
        messages_traites.add(msg_id)
        if len(messages_traites) > 500:
            messages_traites.clear()

        print(f"\n[+] Message reçu de {from_phone} : {text_client}")

        if from_phone not in memoires_clients:
            memoires_clients[from_phone] = []

        memoires_clients[from_phone].append(f"Client: {text_client}")

        # A. Génération de la réponse
        reponse_brute = generer_reponse_koffi(from_phone, text_client)

        # B. Alerte automatique du Chef si réservation validée
        reponse_client = reponse_brute
        match = re.search(r'\[RESERVATION_CONFIRMEE:\s*Nom=(.*?)\s*\|\s*Heure=(.*?)\s*\|\s*Couverts=(.*?)\s*\|\s*Plats=(.*?)\]', reponse_brute)
        if match:
            nom_c = match.group(1).strip()
            heure_c = match.group(2).strip()
            couverts_c = match.group(3).strip()
            plats_c = match.group(4).strip()
            
            reponse_client = re.sub(r'\[RESERVATION_CONFIRMEE:.*?\]', '', reponse_brute).strip()
            
            # Déclenchement de l'alerte au Chef
            threading.Thread(
                target=notifier_chef, 
                args=(nom_c, heure_c, couverts_c, plats_c, from_phone)
            ).start()

        # Envoi de la réponse texte au client
        memoires_clients[from_phone].append(f"Koffi: {reponse_client}")
        sauvegarder_memoires()

        print(f"[>] Koffi répond : {reponse_client}")
        envoyer_message_texte(from_phone, reponse_client)

        # C. Envoi automatique de la photo de la carte si demandée
        mots_menu = ["carte", "menu", "photo", "visuel", "flyer"]
        if any(mot in text_client.lower() for mot in mots_menu):
            print(f"[>] Envoi de la vraie carte au {from_phone}")
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
            self.wfile.write(b"SERVEUR KOFFI ACTIF SUR RENDER 24/7 (CARTE OFFICIELLE & ALERTE CHEF)")

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
    print(f"[*] Serveur Koffi en écoute 24/7 sur le port {port}...")
    server.serve_forever()

if __name__ == '__main__':
    run()
