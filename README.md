![image](https://github.com/user-attachments/assets/94ddf919-c0d4-4ff1-b832-1afe2e354700)

# 🎙️ Real-time Audio Transcription App

Hey there! Welcome to this cool little app that turns your computer talk or your talk into text all thanks to the magic of OpenAI Whisper API! It's like having a super-fast typist listen to everything from your computer's speakers and microphone.

## ✨ What's This App Do?

- Grabs audio from your computer or microphone (or both!)
- Uses OpenAI's latest **gpt-4o-transcribe** model for superior accuracy and reliability
- Shows you the text in a nice, easy-to-use window
- Cleans and summarizes your transcription using OpenAI GPT models
- Automatically falls back to whisper-1 model if the latest model is unavailable

## 🛠️ What You'll Need

- Python 3.7 or newer 
- An OpenAI API key (for both Whisper transcription and GPT post-processing)

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

3. Get your OpenAI API key:
   - Head over to [OpenAI](https://openai.com/index/openai-api/) and sign up
   - Go to your profile and navigate to 'User API keys'
   - Click "Create new secret key"
   - Copy that new key

4. Set up your environment:
   - Create a .env file in the root of the project with:
      - OPENAI_API_KEY="YOUR_SECRET_KEY_HERE"

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

## 🔄 Updating to the Latest Version

To ensure you're using the latest models and features:

1. Update your dependencies:
   ```
   pip install --upgrade -r requirements.txt
   ```

2. The app now uses OpenAI's **gpt-4o-transcribe** model, which offers:
   - Improved accuracy over the old whisper-1 model
   - Better handling of accents and noisy environments
   - More reliable transcription with varying speech speeds
   - Automatic fallback to whisper-1 if the new model is unavailable

## 🆘 Help! Something's Not Working!

If things go sideways:
- Make sure your OPENAI_API_KEY is set up correctly in the .env file. No typos!
- Check if your OpenAI account is still active and has available credits
- Is your internet working? The app needs to talk to OpenAI's servers, so no internet = no transcription
- The app now processes audio in 5-second chunks, so there might be a slight delay compared to real-time streaming
- Run `python test_whisper.py` to verify your setup is working correctly

Happy transcribing! 🎉🎊
