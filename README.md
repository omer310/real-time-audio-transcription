<img width="1205" height="831" alt="image" src="https://github.com/user-attachments/assets/0c5b850d-8951-472b-80e4-d6fbf8fed63a" />


# 🎙️ Live Transcription

So you know how sometimes you're in a meeting, watching a video, or just talking and thinking "man, I wish I had a transcript of this"? Well, this app's got your back. It listens to your computer's audio or your microphone and turns everything into text in real-time. Pretty neat, right?

## What does this thing actually do?

- **Live transcription** - Uses Deepgram's API to transcribe audio as it happens (seriously, it's fast)
- **Speaker diarization** - Figures out who's talking when (Yeah this is not working as of now needs bigger chunks of audio which will not working with the real time I am trying to achieve, but I will keep looking for a solution!)
- **Computer audio or mic** - Capture system audio from videos/calls or use your microphone (or both at once!)
- **AI-powered cleanup** - After transcribing, OpenAI cleans up the text and makes a nice summary
- **Modern UI** - Dark mode with a Teenage Engineering-inspired design (because why not look good while transcribing?)
- **Export everything** - Saves raw transcripts, cleaned versions, and summaries to text files

## What you'll need

- Python 3.7+ (or just download the pre-built .exe if you're on Windows)
- A [Deepgram API key](https://deepgram.com/) for the transcription part
- An [OpenAI API key](https://platform.openai.com/) for the cleanup/summary features
- Internet connection (the APIs need to do their thing)

## Quick start (for developers)

1. Clone this repo:
   ```bash
   git clone https://github.com/omer310/real-time-audio-transcription.git
   cd real-time-audio-transcription
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   DEEPGRAM_API_KEY=your_deepgram_key_here
   OPENAI_API_KEY=your_openai_key_here
   ```

4. Run it:
   ```bash
   python Live_Enhanced.py
   ```

## For non-developers (Easy mode. Still work on this!) 

Just want to use it without dealing with Python? No problem:

1. Download the latest release from the [Releases page](../../releases)
2. Extract the folder somewhere on your computer
3. Create a `.env` file next to the .exe with your API keys (see step 3 above)
4. Double-click `Live Transcription.exe` and you're good to go!

## How to use it

1. Launch the app
2. Pick your audio source (computer audio, microphone, or both)
3. Choose your audio devices from the settings if needed
4. Give your transcription a name (or just use "Untitled", we don't judge)
5. Hit that big "Start Transcription" button
6. Do your thing - talk, play a video, join a meeting, whatever
7. Click "Stop Transcription" when you're done
8. Want it cleaned up? Click "Clean Transcription" or "Summarize" to let AI work its magic
9. Everything gets saved to the `output` folder automatically

## Features you might not notice right away

- **Auto-saves** - Your transcriptions are saved as you go, so you won't lose anything
- **Smart punctuation** - Deepgram adds proper punctuation automatically
- **Word count** - Bottom of the screen shows real-time word count
- **Tabbed interface** - Switch between raw transcription, cleaned version, and summary
- **Settings persist** - The app remembers your audio device choices between sessions
- **List audio devices** - Run `list_audio_devices.py` to see all available audio devices on your system

## Building from source

Want to make your own executable? Check out [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for the full guide. There's even a build script (`build_app.bat`) that does everything for you.

## Troubleshooting

**"API key not found" error:**
Make sure your `.env` file is in the same folder as the executable (or in the project root if running from Python). Double-check for typos in your keys.

**No audio devices showing up:**
Run `list_audio_devices.py` to see what devices are available. On Windows, you might need to install the [VC++ Redistributables](https://aka.ms/vs/17/release/vc_redist.x64.exe).

**Transcription isn't starting:**
Check your internet connection - both Deepgram and OpenAI need to be reachable. Also make sure your API keys are valid and have credits available.

**Audio sounds choppy or cuts out:**
Try adjusting the buffer size in the audio settings, or restart the app. Sometimes audio drivers just need a kick.

## Contributing

Found a bug? Have an idea to make this better? PRs are welcome! Just keep things clean and follow the existing code style. Or open an issue if you just want to chat about it.

## License

MIT License - do whatever you want with this. See [LICENSE](LICENSE) for the boring legal text.

## Shoutout

Big thanks to Deepgram for their awesome transcription API and OpenAI for making text cleanup easy. Also shoutout to Teenage Engineering for the design inspiration - your products look way too good.

---

Built with Python, too much coffee, and the desire to never manually type meeting notes again.

