from flask import Flask, request
import requests
from  datetime import datetime
import time
import os
import urllib.parse
import re

bot_token = os.environ.get("bot_token")
allowed_usernames = os.environ.get("allowed_usernames").split(",")
assemblyai_api_key = os.environ.get("assemblyai_api_key")


app = Flask(__name__)

def parse_text(test_str):

  regex = r"(?:più)?\s?(\d+)\s?(?:euro)?\s?e?\s?(\d*)\s?(?:centesimi)?"

  #test_str = "2 euro e 20"




  matches = re.finditer(regex, test_str, re.MULTILINE)

  for matchNum, match in enumerate(matches, start=1):
      
      #print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))
      
      units =  match.group(1)
      cents = match.group(2)
      #print(units,cents)
  # Note: for Python 2.7 compatibility, use ur"" to prefix the regex and u"" to prefix the test string and substitution.
  result = float(units)
  if cents != "":
    result += float(cents)/100
  if match.group()[0:3] != 'più':
    result *= -1
  return test_str.replace(match.group(),"").strip(),str(result).replace(".",",")


@app.route("/telegram/",methods = ['POST'])
def telegram_message():
    # Get the message JSON from Telegram
    msg = request.get_json()

    # Check if it is a voice message
    if 'voice' not in msg['message'].keys():
        return 'No voice message'
    
    # Check if it has been sent from an allowed user
    if msg['message']['from']['username'] not in allowed_usernames:
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
            'audio_url': audio_url,
            "language_code": "it"
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

    descrizione,importo = parse_text(transcribed_text)
    requests.post("https://hook.eu1.make.com/odaqe8jcw3njnbyalpvhpsfbmkqbauvs",json={'descrizione':descrizione,'importo':importo})

    return "OK"
    

if __name__ == '__main__':
    app.run()