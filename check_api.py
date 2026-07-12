import requests

try:
    print("Sending request to Qwen... (This might take a moment to process)")
    response = requests.post(
        "http://sinbad2ia.ujaen.es:8050/api/chat",
        json={
            "model": "qwen3.5:35b",  
            "messages": [
                {"role": "user", "content": "Hello, what is a BDI agent?"}
            ],
            "stream": False
        },
        timeout=300 # Gives the server 5 full minutes to compute the model matrix
    )
    
    print(response.json()["message"]["content"])

except requests.exceptions.Timeout:
    print("Connection dropped: The server is taking too long to think.")
except requests.exceptions.ConnectionError:
    print("Firewall block: Your laptop cannot reach the server IP. (Turn on VPN!)")