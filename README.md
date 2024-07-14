# 🎙️ Real-time Audio Transcription App

Hey there! Welcome to this cool little app that turns your babbling computer into text, all thanks to the magic of Deepgram's API. It's like having a super-fast typist listening to everything coming out of your computer's speakers. Neat, huh?

## ✨ What's This App Do?

- Grabs audio from your computer.
- Uses Deepgram's fancy API to turn that audio into text.
- Shows you the text in a nice, easy-to-use window.

## 🛠️ What You'll Need

- Python 3.7 or newer 
- A Deepgram API key (don't worry, I'll show you how to get one)

## 🚀 Getting Started

1. Grab the code:
   ```
   git clone https://github.com/your-username/real-time-audio-transcription.git
   cd real-time-audio-transcription
   ```

2. Install the goodies:
   ```
   pip install -r requirements.txt
   ```

3. Get your hands on a Deepgram API key:
   - Pop over to [Deepgram](https://deepgram.com) and sign up. It's free!
   - Once you're in, head to the [API Keys dashboard](https://console.deepgram.com/api-keys).
   - Click "Create API Key" (it's like making a new key for your secret clubhouse)
   - Copy that shiny new key. Guard it with your life!

4. Let your computer know about your new secret key:
   - If you're a Windows fan:
     Open Command Prompt and type:
     ```
     setx DEEPGRAM_API_KEY "paste-your-secret-key-here"
     ```
   - If you're on a Mac or Linux:
     Open Terminal and type:
     ```
     echo 'export DEEPGRAM_API_KEY="paste-your-secret-key-here"' >> ~/.bash_profile
     source ~/.bash_profile
     ```

5. Double-check it worked:
   - Open a fresh terminal window
   - Type: 
     - Windows: `echo %DEEPGRAM_API_KEY%`
     - Mac/Linux: `echo $DEEPGRAM_API_KEY`
   - If you see your key, give yourself a high five!

## 🎉 Let's Run This Thing!

1. Fire it up:
   ```
   python Live.py
   ```

2. Hit "Start Transcription" and let your computer talk to itself.

3. When you're done, click "Stop Transcription". Magic!

4. Check out your transcribed masterpiece in the app window. We've also saved a copy in the `output` folder, you know, for posterity.

## 🤝 Want to Make It Better?

Got ideas? Found a bug? Think you can make it even cooler? Awesome! Feel free to dive in and make changes. Just be nice and send a Pull Request so we can all benefit from your genius.

## 📜 Legal Stuff

This project is under the MIT License. Basically, do whatever you want with it, just don't blame us if something goes wrong. Check out the [LICENSE](LICENSE) file for the boring details.

## 🆘 Help! Something's Not Working!

If things go sideways:
- Make sure that DEEPGRAM_API_KEY is set up right. No typos!
- Check if your Deepgram account is still active. They didn't kick you out, did they?
- Is your internet working? The app needs to talk to Deepgram's servers, so no internet = no transcription.

Happy transcribing! 🎉🎊
