import os
import sys
import traceback
import requests
import json

def main():
    print(f"Python version: {sys.version}")
    
    # Get API key
    api_key = input("Please enter your Deepgram API key: ").strip()
    print(f"API Key: {api_key[:5]}...{api_key[-5:]}")

    try:
        # Download audio file
        print("Downloading audio file...")
        audio_url = "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"
        audio_response = requests.get(audio_url)
        audio_data = audio_response.content

        # Prepare the request to Deepgram API
        url = "https://api.deepgram.com/v1/listen"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav"
        }
        params = {
            "model": "nova-2",
            "language": "en-US"
        }

        # Send request to Deepgram API
        print("Sending request to Deepgram API...")
        response = requests.post(url, headers=headers, params=params, data=audio_data)

        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            print("\nTranscript:")
            print(result["results"]["channels"][0]["alternatives"][0]["transcript"])
            print("\nConnection to Deepgram API successful!")
        else:
            print(f"Error: API request failed with status code {response.status_code}")
            print("Response content:")
            print(response.text)

    except Exception as e:
        print(f"An error occurred: {type(e).__name__}: {e}")
        print("\nFull traceback:")
        traceback.print_exc()

    finally:
        print("\nTest script completed. Press Enter to exit.")
        input()

if __name__ == "__main__":
    main()