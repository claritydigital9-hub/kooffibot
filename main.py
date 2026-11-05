# -*- coding: utf-8 -*-
import os, json, requests, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from google import genai
from google.genai import types

# CONFIGURATION
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "EAAWhxl1ur38BSzCOugMGBybAW0rA7JarcTONY6kPB1GqOu3fnSsfoyqparDXutHbgBfZCoWqSKxZCYp7rI0OdUV7T6ldFrdif69rb2ptJzZCZAbBibzafJ8s0zLBpBM0peRWtmZBa1ruJpR7X1b8Qeke0TF2mkmrnp2XO0WiHVbHO1Vs917WyKLNn7dAELVaUNgZDZD")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "1244852872055806")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mon_token_secret_koffi")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IkgJIlIqDHEl1T4HzCZfcw6H3n1rOcq1IUOYBsQGAKnA")

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
messages_traites = set()
FICHIER_MEMOIRE = "memoires_clients.json"

# PERSISTENCE DE LA MÉMOIRE SUR DISQUE (ZÉRO PERTE AU REDÉMARRAGE)
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

memoires_clients = charger_memoires()

def generer_reponse_koffi(from_phone, text_client):
    # Politesse miroir intelligente
    texte_lower = text_client.lower()
    if "bonsoir" in texte_lower:
        salutation = "Bonsoir"
    elif "bonjour" in texte_lower:
        salutation = "Bonjour"
    else:
        h = datetime.now().hour
        salutation = "Bonjour" if 5 <= h < 14 else "Bonsoir"

    prompt_systeme = f"""Tu es Koffi, le maître d'hôtel chaleureux, poli et très professionnel du restaurant "Le Braisé Lounge & Saveurs d'Ivoire" à Adidogomé (Lomé, Togo).
Ton but est de converser naturellement comme un être humain au téléphone ou sur WhatsApp.

INFORMATIONS DU RESTAURANT :
- Localisation : Lomé, quartier Adidogomé, non loin du grand carrefour / boulevard principal.
- Lien Google Maps officiel : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome
- Téléphone direct / Réservation : +228 90 00 00 00
- Présence en ligne : Nous sommes très actifs sur TikTok (@lebraiselounge) et Instagram !
- Carte & Prix :
  * Poulet braisé entier : 7.000 F CFA | Demi-poulet : 4.000 F CFA
  * Poissons braisés frais (Carpe / Bar) : 5.000 F à 10.000 F CFA selon la taille
  * Brochettes de bœuf assaisonnées : 3.000 F CFA la portion
  * Garba au thon rouge : 1.500 F à 3.000 F CFA
  * Accompagnements : Alloco (1.000 F), Frites, Attiéké

RÈGLES D'OR DE CONVERSATION :
1. MÉMOIRE DU CLIENT : Si le client t'a déjà donné son nom (ex: "chef Lefa"), ses plats, son heure ou le nombre de personnes plus haut dans l'historique, RETIENS-LE et utilise son nom avec respect !
2. QUESTIONS PRÉCÉDENTES : Si le client demande "quel était notre dernier conversation", fais-lui un résumé chaleureux et exact de ce qu'il a réservé ou demandé.
3. QUESTIONS SUR LA LOCALISATION : S'il demande un lien Google Maps ou comment venir, donne-lui directement le lien Google Maps avec plaisir.
4. NATUREL HUMAIN : Sois expressif, courtois, n'utilise pas de phrases toutes faites et ne réinitialise JAMAIS la discussion en redemandant "comment puis-je vous aider" si vous êtes déjà en plein dialogue !
5. Salutation actuelle : Réponds avec "{salutation}" si tu dois saluer."""

    # Historique récent (les 12 derniers échanges)
    historique = memoires_clients.get(from_phone, [])[-12:]
    dialogue_str = "\n".join(historique)
    
    contenu_final = f"""Historique de notre conversation actuelle :
{dialogue_str}

Le client vient d'envoyer :
Client: {text_client}

Ta réponse en tant que Koffi (directe, naturelle et sans répéter inutilement les salutations) :"""

    # Cascade de modèles avec timeout court
    modeles = ["gemini-2.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    for m in modeles:
        try:
            resp = client_gemini.models.generate_content(
                model=m,
                contents=contenu_final,
                config=types.GenerateContentConfig(
                    system_instruction=prompt_systeme,
                    temperature=0.6,
                    max_output_tokens=300
                )
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception as e:
            print(f"[!] Échec sur {m}: {e}")
            continue

    # Réponse humaine contextuelle en cas d'erreur réseau exceptionnelle
    if "maps" in texte_lower or "localisation" in texte_lower:
        return "Voici notre emplacement exact sur Google Maps à Adidogomé : https://maps.google.com/?q=Le+Braise+Lounge+Adidogome+Lome . Nous vous y attendons avec plaisir !"
    return "Bien noté chef ! C'est parfaitement enregistré pour vous au Braisé Lounge. Que puis-je vous préciser d'autre ?"

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

        # Anti-doublons strict
        if msg_id in messages_traites:
            return
        messages_traites.add(msg_id)
        if len(messages_traites) > 500:
            messages_traites.clear()

        print(f"\n[+] Message reçu de {from_phone} : {text_client}")

        if from_phone not in memoires_clients:
            memoires_clients[from_phone] = []

        # Enregistrer le message client dans l'historique
        memoires_clients[from_phone].append(f"Client: {text_client}")

        # Générer la réponse intelligente
        reponse_koffi = generer_reponse_koffi(from_phone, text_client)

        # Enregistrer la réponse de Koffi dans l'historique
        memoires_clients[from_phone].append(f"Koffi: {reponse_koffi}")
        sauvegarder_memoires()

        print(f"[>] Koffi répond : {reponse_koffi}")

        # Envoi WhatsApp direct via Meta
        url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": from_phone,
            "type": "text",
            "text": {"body": reponse_koffi}
        }
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[✓] Statut envoi WhatsApp : {r.status_code}")

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
            self.wfile.write(b"SERVEUR KOFFI ACTIF SUR RENDER 24/7")

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
