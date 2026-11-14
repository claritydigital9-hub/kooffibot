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

# Numéro qui reçoit les alertes de devis / RDV (Directeur GIGC BTP)
NUMERO_DIRECTEUR = os.environ.get("NUMERO_DIRECTEUR", "22897633742")

# Photo sur GitHub
PHOTO_REALISATION_URL = os.environ.get(
    "PHOTO_REALISATION_URL",
    "https://raw.githubusercontent.com/claritydigital9-hub/kooffibot/main/residence_renaissance.jpg",
)

client_gemini = genai.Client(api_key=GEMINI_API_KEY)

historiques = {}
messages_traites = set()


def salutation_lome():
    heure_utc = datetime.utcnow().hour
    return "Bonjour" if 5 <= heure_utc < 18 else "Bonsoir"


def construire_prompt_awa(deja_salue):
    regle_salutation = (
        f"C'est le TOUT PREMIER message du client : commence naturellement par « {salutation_lome()} »."
        if not deja_salue
        else "Tu as DÉJÀ salué ce client : NE RÉPÈTE JAMAIS « Bonjour » ou « Bonsoir ». Enchaîne directement et naturellement (« Avec plaisir », « C'est bien noté », « Parfait », etc.)."
    )

    return f"""Tu es Awa, l'assistante virtuelle officielle de GIGC BTP SARL U (Groupe des Ingénieurs en Génie Civil), basée à Agoè Zongo, Lomé, Togo.
Slogan : « L'efficacité, c'est notre priorité. »

RÈGLE DE CONVERSATION :
{regle_salutation}
- Reste chaleureuse, professionnelle, directe et concise (adaptée à WhatsApp).
- N'écris jamais de texte entre parenthèses ou crochets du type (Photo envoyée) ou [Envoi d'image].

INFORMATIONS OFFICIELLES DE GIGC BTP SARL U :
- Adresse : Agoè Zongo, Lomé, Togo (interventions sur tout le Togo et en Afrique de l'Ouest).
- Horaires : Lundi au Samedi, de 07h30 à 18h30.
- Téléphones : +228 91 06 70 41 / +228 79 76 78 45.
- E-mails : contact@gigcbtp.com / gigcbtp5@gmail.com.
- Site web : https://gigcbtp.com (devis gratuit personnalisé sous 48h).

CATALOGUE DES SERVICES :
A. Génie civil et construction : construction de bâtiments, génie civil et travaux publics.
B. Conception de plans et études : plans de bâtiments et études techniques.
C. Topographie : prestations et relevés topographiques.
D. Forage : services de forage d'eau (NE JAMAIS garantir la présence d'eau ni un débit précis).
E. Électricité et solutions techniques : électricité bâtiment et industrielle, caméras de surveillance, froid bâtiment, fabrication de lampes PVC.
F. Matériaux de construction : vente de ciment, sable fin, sable gros grain, gravier, remblais.
G. Distribution de ciment : distributeur agréé CIMCO et CIMTOGO.
H. Location d'engins et de matériels : camions bennes, chargeuse, compactor Bomag, marteaux-piqueurs, dame sauteuse, brouettes, pelles, pioches, marteaux-masses, meule, échafaudages métalliques.
I. Location d'échafaudages : échafaudages métalliques conformes.
J. Livraison de matériaux : fourniture et livraison sur chantier.
K. Location de matériel événementiel : bâches, chaises, échafaudages démontables.
L. Import-export : matériaux et équipements destinés au BTP.
M. Fabrication de lampes PVC : lampes sur mesure en PVC.

RÉALISATION RÉELLE CONNUE :
- Résidence Renaissance – CNSS (propose d'envoyer l'affiche ou la photo si le client le demande).

RÈGLES STRICTES :
1. N'INVENTE JAMAIS de prix, tarifs, disponibilités d'engins, stocks, garanties ou certifications.
2. Si le client demande un prix ou un devis, QUALIFIE son besoin avec 2 à 3 questions simples (type de projet ou produit, quartier/lieu, superficie ou quantité, et son nom).
3. Si le client demande à voir des réalisations, votre affiche ou des photos, termine ta réponse par : [[ENVOYER_PHOTO_REALISATION]]
4. Dès que le client a donné les infos de base pour son devis ou demande un rendez-vous au bureau d'Agoè Zongo, confirme la transmission à l'équipe technique (retour sous 48h) et ajoute à la toute fin, sur une nouvelle ligne :
[[ALERTE_DIRECTION: Résumé court du besoin, lieu, nom/contact si donné]]
"""


def appeler_gemini(system_prompt, hist, nouveau_message):
    derniere_erreur = ""
    for modele in ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
        try:
            contents = []
            for msg in hist[-10:]:
                contents.append(types.Content(role=msg["role"], parts=[types.Part(text=msg["text"])]))
            contents.append(types.Content(role="user", parts=[types.Part(text=nouveau_message)]))

            response = client_gemini.models.generate_content(
                model=modele,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.5,
                    max_output_tokens=900,
                ),
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            derniere_erreur = f"{modele}: {e}"
            print(f"Erreur Gemini ({modele}): {e}")

    return f"Merci pour votre message. Un conseiller technique de GIGC BTP vous répond au +228 91 06 70 41. (Log: {derniere_erreur[:120]})"


def envoyer_whatsapp_texte(destinataire, texte):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": destinataire, "type": "text", "text": {"body": texte}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code >= 400:
            print(f"Erreur Meta texte ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"Exception Meta texte: {e}")


def envoyer_whatsapp_image(destinataire, image_url, legende=""):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": destinataire, "type": "image", "image": {"link": image_url, "caption": legende}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        if r.status_code >= 400:
            print(f"Erreur Meta image ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"Exception Meta image: {e}")


def traiter_message_utilisateur(expediteur, texte_recu, est_web=False):
    texte_clean = texte_recu.strip()

    hist = historiques.get(expediteur, [])
    deja_salue = len(hist) > 0

    reponse_brute = appeler_gemini(construire_prompt_awa(deja_salue), hist, texte_clean)

    doit_envoyer_photo = "[[ENVOYER_PHOTO_REALISATION]]" in reponse_brute
    match_alerte = re.search(r"\[\[ALERTE_DIRECTION:\s*(.*?)\]\]", reponse_brute, re.DOTALL)

    reponse_finale = re.sub(r"\[\[ENVOYER_PHOTO_REALISATION\]\]", "", reponse_brute)
    reponse_finale = re.sub(r"\[\[ALERTE_DIRECTION:.*?\]\]", "", reponse_finale, flags=re.DOTALL).strip()

    hist.append({"role": "user", "text": texte_clean})
    hist.append({"role": "model", "text": reponse_finale})
    historiques[expediteur] = hist[-12:]

    if not est_web:
        envoyer_whatsapp_texte(expediteur, reponse_finale)
        if doit_envoyer_photo and PHOTO_REALISATION_URL:
            envoyer_whatsapp_image(
                expediteur,
                PHOTO_REALISATION_URL,
                "Nos services et réalisations — GIGC BTP SARL U (Agoè Zongo, Lomé)",
            )

    if match_alerte:
        resume = match_alerte.group(1).strip()
        canal = "Site Web (gigcbtp.com)" if est_web else f"WhatsApp (+{expediteur})"
        msg_alerte = (
            f"🔔 NOUVELLE DEMANDE QUALIFIÉE — GIGC BTP\n"
            f"• Canal : {canal}\n"
            f"• Dossier : {resume}\n"
            f"• Dernier message : {texte_clean}"
        )
        threading.Thread(target=envoyer_whatsapp_texte, args=(NUMERO_DIRECTEUR, msg_alerte), daemon=True).start()

    return reponse_finale


class WebhookHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/webhook":
            params = parse_qs(parsed.query)
            mode = params.get("hub.mode", [""])[0]
            token = params.get("hub.verify_token", [""])[0]
            challenge = params.get("hub.challenge", [""])[0]
            if mode == "subscribe" and token == VERIFY_TOKEN:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(challenge.encode("utf-8"))
                return
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Serveur Awa - GIGC BTP SARL U actif 24/7.")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        data = json.loads(body) if body else {}

        if parsed.path == "/chat-web":
            message = (data.get("message") or "").strip()
            session_id = (data.get("session_id") or "visiteur_web").strip()
            if not message:
                self.send_response(400)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Message vide"}).encode("utf-8"))
                return

            reponse = traiter_message_utilisateur(f"web_{session_id}", message, est_web=True)
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reponse}).encode("utf-8"))
            return

        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    for msg in value.get("messages", []):
                        msg_id = msg.get("id")
                        if msg_id in messages_traites:
                            continue
                        messages_traites.add(msg_id)
                        if len(messages_traites) > 1000:
                            messages_traites.clear()

                        expediteur = msg.get("from", "")
                        if msg.get("type") == "text":
                            corps = msg["text"]["body"]
                            threading.Thread(
                                target=traiter_message_utilisateur,
                                args=(expediteur, corps, False),
                                daemon=True,
                            ).start()
        except Exception as e:
            print(f"Erreur webhook: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Demarrage serveur Awa GIGC BTP sur le port {port}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
  
