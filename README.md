# 🎙️ Real-time Audio Transcription App

Hey there! Welcome to this cool little app that turns your computer talk or your talk into text all thanks to the magic of Deepgram's and Open AI API's. It's like having a super-fast typist listen to everything from your computer's speakers and microphone if you want.

## ✨ What's This App Do?

- Grabs audio from your computer or microphone. (Listening from both is coming soon)
- Uses Deepgram's fancy API to turn that audio into text.
- Shows you the text in a nice, easy-to-use window. (UPDATED!!!!)
- Cleans and summarizes your transcription using Open AI API. (NEW!)

## 🛠️ What You'll Need

- Python 3.7 or newer 
- A Deepgram API key (don't worry, I'll show you how to get one)
- Open AI API key

## 🚀 Getting Started

1. Grab the code:
   ```
   git clone https://github.com/your-username/real-time-audio-transcription.git
   cd real-time-audio-transcription
   ```

2. Install the neccesitis:
   ```
   pip install -r requirements.txt
   ```

3. Get your hands on a Deepgram API key:
   - Pop over to [Deepgram](https://deepgram.com) and sign up. It's free!
   - Once you're in, head to the [API Keys dashboard](https://console.deepgram.com/api-keys).
   - Click "Create API Key" 
   - Copy that new key.

4.  Get your hands on an OPENAI API key:
   - Pop over to [Open AI]([https://openai.com/index/openai-api/]) and sign up.
   - Go to 'your profile' and head to the 'User API keys'
   - Click "Create new secret key"
   - Copy that new key. 

5. Let your computer know about your new secret key:
   - create a .env file in the root of the project and provide it with the following: 
      - DEEPGRAM_API_KEY=" YOUR SECCRT KEY HERE"
      - OPENAI_API_KEY=" YOUR SECCRT KEY HERE"

## 🎉 Let's Run This Thing!

1. Fire it up:
   ```
   python Live.py
   ```
2. Name your transcription.

3. Hit "Start Transcription" and let your computer talk to itself or you talk to yourself.

4. When you're done, click "Stop Transcription". Magic!

5. You can hit the big red button 'clear' to clear your previous transcription.

6. Check out your transcribed masterpiece in the app window. We've also saved a copy in the `output` folder. You will have three files "Name, Name_cleaned and Name_summary"

## 🤝 Want to Make It Better?

Got ideas? Found a bug? Think you can make it even cooler? Awesome! Feel free to dive in and make changes. Just be nice and send a Pull Request so we can all benefit from your genius.

## 📜 Legal Stuff

This project is under the MIT License. Do whatever you want with it, just don't blame me if something goes wrong. Check out the [LICENSE](LICENSE) file for the boring details.

## 🆘 Help! Something's Not Working!

If things go sideways:
- Make sure that DEEPGRAM_API_KEY and OPENAI_API_KEY set up right. No typos!
- Check if your Deepgram and OPENAI accounts are still active. They didn't kick you out, did they?
- Is your internet working? The app needs to talk to Deepgram's servers, so no internet = no transcription.

Happy transcribing! 🎉🎊
