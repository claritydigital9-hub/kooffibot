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
messages_traites = set()

def generer_reponse_koffi(historique, prompt):
    # Appel direct sur les modèles officiels recommandés par Google
    modeles = ['gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gemini-flash-lite-latest']
    for m in modeles:
        try:
            resp = client_gemini.models.generate_content(
                model=m,
                contents=historique,
                config=types.GenerateContentConfig(system_instruction=prompt, temperature=0.3)
            )
            if resp.text:
                return resp.text
        except Exception as e:
            print(f"Modèle {m} indisponible, bascule...", flush=True)
    return "Bonjour ! Je suis Koffi de Le Braisé Lounge. Bien reçu, comment puis-je vous aider ?"

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
        
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            body = challenge.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            print(">>> Webhook Meta vérifié avec succès !", flush=True)
        else:
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
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return
                
            msg = messages[0]
            msg_id = msg.get('id', '')
            
            # FILTRE ANTI-DOUBLON STRICT
            if msg_id and msg_id in messages_traites:
                print(f"[!] Message déjà traité ({msg_id}), ignoré.", flush=True)
                return
            if msg_id:
                messages_traites.add(msg_id)
                # Garde les 500 derniers identifiants en mémoire
                if len(messages_traites) > 500:
                    messages_traites.pop()
                
            from_phone = msg.get('from', '')
            text_body = msg.get('text', {}).get('body', '')
            
            if not text_body:
                return
                
            print(f"\n[!] Message reçu ({from_phone}) : {text_body}", flush=True)
            
            if from_phone not in memoires_clients:
                memoires_clients[from_phone] = []
            memoires_clients[from_phone].append(f"Client: {text_body}")
            
            h = datetime.now().hour
            salutation = "Bonjour" if 5 <= h < 17 else "Bonsoir"
            
            prompt = f"""Tu es Koffi, le maître d'hôtel chaleureux, poli et direct du restaurant "Le Braisé Lounge & Saveurs d'Ivoire" à Lomé (Adidogomé).
Il est actuellement {h}h à Lomé : dis "{salutation}" uniquement si c'est le début de la conversation.

RÈGLES DE CONVERSATION NATURELLE :
1. Tu t'appelles KOFFI. Si le client te demande ton prénom, ton nom ou qui tu es, dis simplement que tu es Koffi, son maître d'hôtel.
2. Si une réservation est DÉJÀ confirmée dans l'historique et que le client pose une autre question (ex : demande ton nom, demande des conseils, ou dit merci) : RÉPONDS DIRECTEMENT À SA QUESTION sans répéter bêtement la confirmation de réservation !
3. Reste concis, poli et réactif. Va droit au but comme un vrai serveur togolais attentif.
4. Carte : Poulet braisé (7.000 F entier / 4.000 F demi), Poissons braisés frais (5.000 à 10.000 F selon taille), Garba au thon (1.500 à 3.000 F), Brochettes (3.000 F).
5. Localisation : Lomé, Adidogomé non loin du boulevard principal.
6. Réservation : Dès que tu as le nom, l'heure et le nombre de personnes, confirme la table une seule fois clairement."""

            historique_texte = "\n".join(memoires_clients[from_phone])
            reponse = generer_reponse_koffi(historique_texte, prompt)
            
            memoires_clients[from_phone].append(f"Koffi: {reponse}")
            print(f"[!] Koffi répond : {reponse}", flush=True)
            
            url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
            payload = {"messaging_product": "whatsapp", "to": from_phone, "type": "text", "text": {"body": reponse}}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"Statut envoi Meta : {r.status_code}", flush=True)
            
        except Exception as e:
            print(f"Erreur d'exécution : {e}", flush=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"SERVEUR KOFFI EN LIGNE SUR LE PORT {port}", flush=True)
    HTTPServer(('0.0.0.0', port), MetaWebhookHandler).serve_forever()
