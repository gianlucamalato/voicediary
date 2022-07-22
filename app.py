from flask import Flask, request
import requests
from  datetime import datetime
import time
import os
import urllib.parse


bot_token = os.environ.get("bot_token")
allowed_username = os.environ.get("allowed_username")
assemblyai_api_key = os.environ.get("assemblyai_api_key")
notion_api_key = os.environ.get("notion_api_key")
notion_block_id = os.environ.get("notion_block_id")


app = Flask(__name__)


@app.route("/telegram/",methods = ['POST'])
def telegram_message():
    # Get the message JSON from Telegram
    msg = request.get_json()

    # Check if it is a voice message
    if 'voice' not in msg['message'].keys():
        return 'No voice message'
    
    # Check if it has been sent from an allowed user
    if msg['message']['from']['username'] != allowed_username:
        return 'User not allowed'

    # Get Telegram voice message file id
    file_id = msg['message']['voice']['file_id']

    # Get public URL file id
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
  
    # Get Telegram file path
    telegram_filepath =  requests.get(url).json()['result']['file_path']

    # Telegram voice message public URL
    audio_url = f'https://api.telegram.org/file/bot{bot_token}/{telegram_filepath}'


    transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
    polling_endpoint = "https://api.assemblyai.com/v2/transcript/"

    header = {
        'authorization': assemblyai_api_key,
        'content-type': 'application/json'
    }

    transcript_request = {
            'audio_url': audio_url
    }

    # Send voice message to Assembly AI
    transcript_response = requests.post(
        transcript_endpoint,
        json=transcript_request,
        headers=header
    )

    # Wait for transcript completion
    while True:
        print("Polling...")
        polling_response = requests.get(polling_endpoint + transcript_response.json()['id'], headers=header)
        polling_response = polling_response.json()
        if polling_response['status'] == 'completed':
            break

        time.sleep(3)
    
    transcribed_text = polling_response['text']

    # Add to notion page
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    url = f"https://api.notion.com/v1/blocks/{notion_block_id}/children"

    headers = {
        "Accept": "application/json",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {notion_api_key}"
    }



    payload = {'children':[
                            {"type": "heading_1","heading_1":{"rich_text": [{"type": "text","text": {"content": ts}}]}},
                            {
                            "type": "paragraph",
                            "paragraph": {
                                    "rich_text": [
                                                
                                                {"type": "text","text": {"content": transcribed_text},'annotations':{'bold':False}},
                                                ],
                                    "color": "default",
                                }
                                },
                            {'type':'divider','divider':{}}
    ]}

    # Add the transcribed message to Notion page
    response = requests.patch(url, headers=headers, json=payload)
    chat_id = msg['message']['chat']['id']
    params = {'chat_id': chat_id}
    print(response.text)
    # Send a Telegram message with the status
    if response.status_code == 200:
        params['text'] = 'Message added to the diary'    

    else:
        params['text'] = 'Error adding message to the diary'   

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?"+urllib.parse.urlencode(params)
    requests.get(url)

    return "OK"
    

if __name__ == '__main__':
    app.run()