from http.server import HTTPServer, BaseHTTPRequestHandler
import json, requests, os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from google import genai
from google.genai import types

PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID', '1244852872055806')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', 'EAAWhxl1ur38BSzCOugMGBybAW0rA7JarcTONY6kPB1GqOu3fnSsfoyqparDXutHbgBfZCoWqSKxZCYp7rI0OdUV7T6ldFrdif69rb2ptJzZCZAbBibzafJ8s0zLBpBM0peRWtmZBa1ruJpR7X1b8Qeke0TF2mkmrnp2XO0WiHVbHO1Vs917WyKLNn7dAELVaUNgZDZD')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AQ.Ab8RN6IkgJIlIqDHEl1T4HzCZfcw6H3n1rOcq1IUOYBsQGAKnA')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'mon_token_secret_koffi')

client_gemini = genai.Client(api_key=GEMINI_API_KEY)
memoires_clients = {}

class MetaWebhookHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        mode = query.get('hub.mode', [''])[0]
        token = query.get('hub.verify_token', [''])[0]
        challenge = query.get('hub.challenge', [''])[0]
        
        # 1. Verification Meta Webhook
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            body = challenge.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            print(">>> Webhook Meta vérifié avec succès !")
        else:
            # 2. Ping de sante Render ou visite web
            body = b"SERVEUR KOFFI ACTIF SUR RENDER 24/7"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            messages = changes.get('value', {}).get('messages', [])
            if not messages: return
            
            from_phone = messages[0].get('from', '')
            text_body = messages[0].get('text', {}).get('body', '')
            if not text_body: return
            
            print(f"\n[!] Message client ({from_phone}) : {text_body}")
            if from_phone not in memoires_clients:
                memoires_clients[from_phone] = []
            memoires_clients[from_phone].append(f"Client: {text_body}")
            
            h = datetime.now().hour
            salutation = "Bonjour" if 5 <= h < 17 else "Bonsoir"
            
            prompt = f"""Tu es Koffi, le maître d'hôtel de "Le Braisé Lounge" à Lomé (Adidogomé).
Il est actuellement {h}h à Lomé : dis strictement "{salutation}" en saluant.
RÈGLES :
- Sois poli, concis, direct et professionnel.
- Carte : Poulet braisé (7.000 F / 4.000 F demi), Poissons braisés frais (5.000 à 10.000 F), Garba au thon (1.500 à 3.000 F), Brochettes (3.000 F).
- Réservation : Il te faut obligatoirement (1) Le nom, (2) L'heure, (3) Le nombre de personnes.
- Si le client a déjà donné une info dans l'historique ci-dessous, NE LA REDEMANDE PAS ! Demande uniquement ce qui manque.
- Dès que tu as les 3 infos, confirme immédiatement la table."""

            historique_texte = "\n".join(memoires_clients[from_phone])
            gemini_resp = client_gemini.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=historique_texte,
                config=types.GenerateContentConfig(system_instruction=prompt, temperature=0.3)
            )
            reponse = gemini_resp.text
            memoires_clients[from_phone].append(f"Koffi: {reponse}")
            print(f"[!] Koffi répond : {reponse}")
            
            url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": from_phone, "type": "text", "text": {"body": reponse}}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Statut envoi Meta : {r.status_code}")
        except Exception as e:
            print(f"Erreur : {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"SERVEUR KOFFI EN LIGNE SUR LE PORT {port}")
    HTTPServer(('0.0.0.0', port), MetaWebhookHandler).serve_forever()
