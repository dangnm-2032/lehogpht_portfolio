import os, certifi

os.environ["SSL_CERT_FILE"] = certifi.where()

from pyngrok import ngrok

ngrok.set_auth_token("30RqXHIWMSW7fhMBAsiyINnhGUU_5KgSzcfWmt922S8xc7uF7")

# expose local port 8000
public_url = ngrok.connect(6000)
print("Public URL:", public_url)

while True:
    pass